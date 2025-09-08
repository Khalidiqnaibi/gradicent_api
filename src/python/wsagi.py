"""
Dispatcher WSGI app to mount two Flask apps under one process using Werkzeug's DispatcherMiddleware.

How it works:
- Tries to autodiscover your *main* Flask app and your *legacy* Flask app by attempting to import
  common module names and locating either a Flask instance or a factory function named `create_app` / `create_legacy_app`.
- Exposes a WSGI callable named `application` suitable for PythonAnywhere / any WSGI server.
- Mounts the legacy app under the URL prefix "/legacy". Change the prefix if you want a different path.

USAGE:
1. Put this file in your project root (same folder as your other app modules), or adjust PYTHONPATH so your app modules are importable.
2. If autodiscovery fails, edit the CANDIDATES_MAIN or CANDIDATES_LEGACY lists below to include the actual module names.
3. In PythonAnywhere Web UI, point the WSGI file to import `application` from this module (e.g. `from app import application`).

NOTE: This script makes a best effort to locate apps. If your apps require special init args for factory calls, modify the code
to call them with the needed arguments or export a plain Flask instance variable (commonly `app` or `application`).

"""


import sys
import os
import importlib
import inspect
from typing import Optional, Tuple
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# If your project root is not the current working directory when WSGI loads,
# add it to sys.path. Adjust if necessary.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _find_flask_app_from_module(module) -> Optional[Flask]:
    """Return a Flask application instance if present in the given module, else None."""
    for attr_name in ("application", "app"):
        if hasattr(module, attr_name):
            candidate = getattr(module, attr_name)
            if isinstance(candidate, Flask):
                return candidate

    # If module provides create_app or similar factory, try calling it (best-effort).
    for factory_name in ("create_app", "create_main_app", "create_legacy_app"):
        if hasattr(module, factory_name) and callable(getattr(module, factory_name)):
            try:
                app_obj = getattr(module, factory_name)()
                if isinstance(app_obj, Flask):
                    return app_obj
            except TypeError:
                # Factory might require arguments; can't call it safely here.
                pass
    return None


def autodiscover_app(candidates: Tuple[str, ...]) -> Tuple[Optional[Flask], Optional[str]]:
    """
    Try to import modules by name and find a Flask app instance or factory.
    Returns (app_instance_or_None, module_name_or_None)
    """
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        app_obj = _find_flask_app_from_module(mod)
        if app_obj is not None:
            return app_obj, mod_name
        # if module itself is already a Flask instance (rare), check that too
        if isinstance(mod, Flask):
            return mod, mod_name
    return None, None


# Common module name guesses — update these to match your project modules if autodiscover fails.
CANDIDATES_MAIN = (
    "main",        # common
    #"app",         # common
    #"wsgi",        # sometimes
    "server",      # sometimes
    "application", # sometimes
    "myapp",       # fallback
)

CANDIDATES_LEGACY = (
    "app",
    "legacy",
    "legacy_app",
    "legacy_routes",
    "old_app",
    "prev_app",
    "previous_app",
)


main_app, main_mod = autodiscover_app(CANDIDATES_MAIN)
legacy_app, legacy_mod = autodiscover_app(CANDIDATES_LEGACY)


# Helpful diagnostics if import failed (printed only on WSGI startup)
_missing = []
if main_app is None:
    _missing.append("main app")
if legacy_app is None:
    _missing.append("legacy app")

if _missing:
    # Do not raise here — instead create a minimal placeholder app with helpful pages so WSGI still loads.
    from flask import Flask, jsonify, Response

    placeholder = Flask("placeholder_loader")

    @placeholder.route("/")
    def placeholder_index():
        notes = {
            "status": "dispatcher started with missing apps",
            "missing": _missing,
            "advice": "Edit app.py CANDIDATES_MAIN/CANDIDATES_LEGACY to include your actual module names, or export a plain Flask instance named `app`/`application` from those modules."
        }
        return jsonify(notes)

    # If main app is missing, serve placeholder at root to avoid 500 errors.
    if main_app is None:
        main_app = placeholder
    # If legacy missing, create an empty app that simply reports missing
    if legacy_app is None:
        legacy_app = Flask("legacy_placeholder")
        @legacy_app.route("/")
        def legacy_placeholder():
            return Response("Legacy app not found. Update CANDIDATES_LEGACY in app.py", status=404)


# If both apps are actually the same object, we avoid mounting twice.
if main_app is legacy_app:
    # Mount main app as the single application; legacy will be available at its own routes.
    application = main_app
else:
    # Mount legacy app under the '/legacy' prefix. Change prefix if you want a different mountpoint.
    application = DispatcherMiddleware(main_app, {
        '/legacy': legacy_app
    })


# ---- Development helper ----
# If you run this file directly (python app.py) it starts a local dev server using werkzeug.
if __name__ == "__main__":
    try:
        # Prefer to use the main_app Flask run if available; otherwise fall back to werkzeug.serving.
        host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
        port = int(os.environ.get("FLASK_RUN_PORT", 5000))
        debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

        # If application is DispatcherMiddleware, run the main_app's server (legacy will be reachable at /legacy).
        # main_app should already be a Flask instance here.
        if isinstance(main_app, Flask):
            print(f"Starting development server for main app (module: {main_mod}), legacy mounted at /legacy (module: {legacy_mod})")
            main_app.run(host=host, port=port, debug=debug)
        else:
            # fallback: use werkzeug's run_simple to serve the DispatcherMiddleware
            from werkzeug.serving import run_simple
            print("Starting werkzeug run_simple for DispatcherMiddleware")
            run_simple('127.0.0.1', port, application, use_debugger=debug, use_reloader=debug)
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        raise
