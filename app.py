"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

import os
from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, initialize_app

from services.subscription_service import SubscriptionService
from binder import FirebaseCrudAdapter, BinderMedical, BinderBusiness, UnitedFirebaseAdapter

from auth.auth_service import AuthService  # using the new AuthService
from services.user_service import UserService
from payments.stripe_provider import StripePaymentProvider
from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint
from routes.payments_routes import payments_blueprint
from routes.auth_routes import auth_blueprint
from routes.frontend_routes import frontend_blueprint
from routes.file_routes import file_routes
from config import DefaultConfig


def _resolve_file_path(path_from_config: str) -> str:
    """
    Try to make config paths robust:
    - If path exists as given, return it.
    - Otherwise, try to resolve it relative to project base dir.
    - Otherwise return the original (so caller can fail with a clear error).
    """
    if not path_from_config:
        return path_from_config

    # if already absolute and exists, use it
    if os.path.isabs(path_from_config) and os.path.exists(path_from_config):
        return path_from_config

    # attempt to resolve relative to project base dir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base_dir, os.path.basename(path_from_config))
    if os.path.exists(candidate):
        return candidate

    # last attempt: join full relative path from base_dir
    candidate2 = os.path.join(base_dir, path_from_config)
    if os.path.exists(candidate2):
        return candidate2

    # give back original — caller will likely raise useful error if it's wrong
    return path_from_config


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(DefaultConfig())

    # Ensure there's a JWT secret available for AuthService
    jwt_secret = app.config.get("JWT_SECRET") or app.config.get("SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("Missing JWT_SECRET or SECRET_KEY in app config for AuthService")

    # Resolve credential and oauth secret file paths robustly
    firebase_cred_path = _resolve_file_path(app.config["FIREBASE"]["credentials_path"])
    oauth_secrets_path = _resolve_file_path(app.config.get("OAUTH_CLIENT_SECRETS_FILE", ""))

    if not os.path.exists(firebase_cred_path):
        raise RuntimeError(f"Firebase credentials file not found: {firebase_cred_path}")
    # Initialize Firebase only once (safe for reloading)
    cred = credentials.Certificate(firebase_cred_path)
    if not firebase_admin._apps:
        initialize_app(cred, {
            'databaseURL': app.config["FIREBASE"]["databaseURL"],
            'storageBucket': app.config["FIREBASE"]["storageBucket"]
        })

    # Adapter + domain binders
    united_firebase_adapter = UnitedFirebaseAdapter(root_path="Gradicent")
    legacy_firebase_adapter_medical = FirebaseCrudAdapter(root_path="drs")

    binders = {
        "medical": BinderMedical(united_firebase_adapter),
        "business": BinderBusiness(united_firebase_adapter),
    }

    app.config.setdefault("BINDERS", binders)

    # Auth
    google_config = {
        "client_secrets_path": oauth_secrets_path,
        "redirect_uri": app.config["OAUTH_REDIRECT_URI"],
        "scopes": app.config.get("OAUTH_SCOPES", ["openid", "email", "profile"]),
    }

    auth = AuthService(
        adapter=united_firebase_adapter,
        legacy_adapter=legacy_firebase_adapter_medical,
        google_config=google_config,
        jwt_secret=jwt_secret,
        # optional: access_token_ttl=3600, refresh_token_ttl=2592000
    )

    auth_services = {
        "medical": auth,
        "business": auth,
    }

    # services/adapters
    payment_provider = StripePaymentProvider(app.config["STRIPE_API_KEY"])
    sub = SubscriptionService(united_firebase_adapter, payment_provider)
    subscription_services = {
        "medical": sub,
        "business": sub,
    }

    # register blueprints and pass factories via app extensions
    app.register_blueprint(gaia_blueprint, url_prefix=app.config["GAIA_ROUTE_PREFIX"])
    app.register_blueprint(binder_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(payments_blueprint, url_prefix=app.config["PAYMENT_ROUTE_PREFIX"])
    app.register_blueprint(auth_blueprint, url_prefix=app.config["AUTH_ROUTE_PREFIX"])
    app.register_blueprint(file_routes, url_prefix=app.config["FILE_ROUTE_PREFIX"])
    app.register_blueprint(frontend_blueprint, url_prefix=app.config["FRONT_ROUTE_PREFIX"])

    # Attach services for controllers to pull from app context
    app.extensions.setdefault("services", {})
    app.extensions["services"].update({
        "auth_services": auth_services,
        "subscription_services": subscription_services,
        "payment_provider": payment_provider,
        "binders": binders,
    })

    return app


# --- WSGI entrypoint variable (used by PythonAnywhere / uWSGI) ---
# Creating `app` at module level is deliberate so WSGI can import it:
app = create_app()
