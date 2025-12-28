"""
frontend_routes.py
------------------
Flask Blueprint providing all frontend (template) routes for Binder.

Why:
- Move UI/template routes out of api.py into a single, testable blueprint.
- Keep each route small and readable. Use helper functions (auth, user_data)
  imported from a central helpers module to avoid duplication and circular imports.
"""

from typing import Any, Dict
import logging

from flask import Blueprint, render_template, redirect,current_app, request, session, jsonify
from decorators.req_login import require_login
from utils.get_plan_status import compute_plan_status
from utils.codes import gencode , save_code,save_seccode

logger = logging.getLogger(__name__)


frontend_blueprint = Blueprint(
    "frontend",
    __name__,
    template_folder="templates", 
)

@frontend_blueprint.route("/", methods=["GET"])
def home() -> str:
    """Landing page."""
    return render_template("index.html")


@frontend_blueprint.route("/med", methods=["GET"])
def med() -> str:
    """Marketing page for Binder Medical; records source param into session."""
    session["source"] = request.args.get("src", "organic")
    return render_template("med.html")


@frontend_blueprint.route("/products", methods=["GET"])
def products() -> str:
    """Products page."""
    return render_template("watches.html")


@frontend_blueprint.route("/about", methods=["GET"])
def about() -> str:
    """About page."""
    return render_template("about.html")


@frontend_blueprint.route("/contact", methods=["GET"])
def contact() -> str:
    """Contact page."""
    return render_template("contact.html")


@frontend_blueprint.route("/privacy", methods=["GET"])
def privacy() -> str:
    """Privacy policy page."""
    return render_template("privacy.html")


@frontend_blueprint.route("/terms", methods=["GET"])
def terms() -> str:
    """Terms & conditions page."""
    return render_template("terms.html")


@frontend_blueprint.route("/ahha", methods=["GET"])
def fooled() -> str:
    """Easter egg page."""
    return render_template("fooled.html")

@frontend_blueprint.route("/med_sub", methods=["GET"])
def med_sub() -> str:
    """
    Show medical plan selection. Pass Paddle client token to template if available.
    This keeps client-side integration with Paddle minimal.
    """
    # session["appname"] = "Binder Medical"
    # paddle_customer_id = session.get("paddle_customer_id", None)
    # token = None
    # try:
    #     token = get_client_token(customer_id=paddle_customer_id)
    # except Exception as exc:  # keep server resilient
    #     logger.warning("Failed to get paddle client token: %s", exc)
    return render_template("plans.html")


@frontend_blueprint.route("/medsub_ar", methods=["GET"])
def med_sub_ar() -> str:
    """Arabic med subscription page."""
    session["appname"] = "Binder Medical"
    return render_template("basic - ar.html")
    
@frontend_blueprint.route("/login", methods=["GET"])
def login_page() -> str:
    """Render login page."""
    return render_template("logme.html")

@frontend_blueprint.route("/logme", methods=["GET"])
def logme_page() -> str:
    """Render login page."""
    return render_template("logme.html")


@frontend_blueprint.route("/logme_ar", methods=["GET"])
def login_page_ar() -> str:
    """Render Arabic login page."""
    return render_template("login - ar.html")


@frontend_blueprint.route("/protected_area", methods=["GET"])
@require_login
def protected_area() -> Any:
    """
    Simple redirect wrapper after login to the main app page.
    Keeps old behavior: log the login event and redirect to /home_page
    """
    return redirect("/home_page")


@frontend_blueprint.route("/logout", methods=["GET"])
def logout() -> Any:
    """Clear session and redirect to login (preserve binder choice)."""
    binder_choice = session.get("binder", "med")
    session.clear()
    session["binder"] = binder_choice
    session["donee"] = False
    return redirect("/logme")

'''
Authenticated pages (page routing wrappers)

The pattern used here: small wrapper that enforces login and sets session['page'],
then redirects to fetch_user_data which will compute the correct template.
'''
def _render_protected_page(page_name: str) -> Any:
    """
    Helper to set session page and redirect to fetch_user_data route which renders
    the real template after preparing user_data. Kept small per standards.
    """
    session["page"] = page_name
    binder = session["binder"]
    if binder in ["medical"]:
        res = "/Binder_medical"
    elif binder in ["business"]:
        res = "/Binder_business"
        
    return res

@frontend_blueprint.route("/acc", methods=["GET"])
@require_login
def acc() -> Any:
    """Account wrapper."""
    return redirect(_render_protected_page("acc"))


@frontend_blueprint.route("/home_page", methods=["GET"])
@require_login
def home_page() -> Any:
    """Home wrapper."""
    return redirect(_render_protected_page("home"))


@frontend_blueprint.route("/support", methods=["GET"])
@require_login
def support() -> Any:
    """Support wrapper."""
    return redirect(_render_protected_page("support"))


@frontend_blueprint.route("/settings", methods=["GET"])
@require_login
def settings() -> Any:
    """Settings wrapper."""
    return redirect(_render_protected_page("settings"))


@frontend_blueprint.route("/stats", methods=["GET"])
@require_login
def stats() -> Any:
    """Stats wrapper."""
    return redirect(_render_protected_page("stats"))

@frontend_blueprint.route("/data/<client>", methods=["GET"])
@require_login
def set_curr_client(client) -> Any:
    """Data redirect for a client details."""
    client = int(client)
    if (client - 1) >= 0:
        client -=1
    elif client == -1:
        pass
    else:
        client = 0
    session["client"] = client
    return redirect("/data")

@frontend_blueprint.route("/data", methods=["GET"])
@require_login
def data() -> Any:
    """Data wrapper for client details."""
    return redirect(_render_protected_page("data"))

@frontend_blueprint.route("/srch",methods=["GET"])
@require_login
def srch() -> Any:
    """srch wrapper."""
    return redirect(_render_protected_page("srch"))

@frontend_blueprint.route("/search_stats" , methods = ["GET"])
@require_login
def search_stats():
    ''' render clients on srch.html'''
    session["clients"] = request.args.get("clients")
    return redirect(_render_protected_page("search_stats"))

@frontend_blueprint.route("/back", methods=["GET"])
@require_login
def back() -> Any:
    """Back wrapper."""
    
    return redirect(_render_protected_page("back"))

@frontend_blueprint.route("/appointments", methods=["GET"])
@require_login
def appointments_route():
    """appointments wrapper."""
    return redirect(_render_protected_page("appointments"))

@frontend_blueprint.route("/lab", methods=["GET"])
def lab_public() -> str:
    """Public lab page (marketing)."""
    return render_template("Labratory.html")


@frontend_blueprint.route("/Binder_medical", methods=["GET"])
@require_login
def binder_medical() -> Any:
    """
    Entry point for medical binder (replicates previous behavior).
    The heavy lifting (checking settings, trial, and rendering correct template)
    remains in fetch_user_data (keeps separation of concerns).
    """
    session["binder"] = "medical"
    page = session.get("page","home")
    if page == "data":
        return render_template(f"{page}.html", client = session.get("client",1))
    if page == "back":
        session["page"] = "srch"
        return render_template(f"srch.html", client = session.get("client",1))
    
    if page == "search_stats":
        clients = session["clients"]
        session["page"] = "srch" 
        return render_template(f"srch.html", clients = clients)


    return render_template(f"{page}.html")

@frontend_blueprint.route("/Binder_business", methods=["GET"])
@require_login
def binder_business() -> Any:
    """
    Entry point for business binder (replicates previous behavior).
    The heavy lifting (checking settings, trial, and rendering correct template)
    remains in fetch_user_data (keeps separation of concerns).
    """
    session["binder"] = "business"
    page = session.get("page","home")
    if page == "data":
        return render_template(f"{page}.html", client = session.get("client",1))
    if page == "back":
        session["page"] = "srch"
        return render_template(f"srch.html", client = session.get("client",1))
    
    if page == "search_stats":
        clients = session["clients"]
        session["page"] = "srch" 
        return render_template(f"srch.html", clients = clients)


    return render_template(f"{page}.html")

@frontend_blueprint.route("/Binder_labratory", methods=["GET"])
@require_login
def binder_laboratory() -> Any:
    """Entry point for lab binder type."""
    session["binder"] = "lab"
    return redirect("/fetchUserData")


def register_frontend(app) -> None:
    """
    Register the frontend blueprint on the Flask app.

    Usage (in app.py or routes/__init__.py):

        from routes.frontend_routes import register_frontend
        register_frontend(app)

    """
    app.register_blueprint(frontend_blueprint)
    logger.info("frontend blueprint registered")
