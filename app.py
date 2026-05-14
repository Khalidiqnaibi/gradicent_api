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
from authlib.integrations.flask_client import OAuth
import json

from services.subscription_service import SubscriptionService
from services.file_service import FileService
from binder import (
    SupabaseAdapter,
    SupabaseFileStorageAdapter,
    BinderMedical, 
    BinderBusiness, 
)

from auth.auth_service import AuthService
from payments.stripe_provider import StripePaymentProvider
from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint
from routes.payments_routes import payments_blueprint
from routes.auth_routes import auth_blueprint
from routes.frontend_routes import frontend_blueprint
from routes.file_routes import file_routes
from config import DefaultConfig
from services.binder_service import BinderService, BinderServiceError


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
    oauth = OAuth(app)

    # Ensure there's a JWT secret available for AuthService
    jwt_secret = app.config.get("JWT_SECRET") or app.config.get("SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("Missing JWT_SECRET or SECRET_KEY in app config for AuthService")

    # Resolve credential and oauth secret file paths robustly
    oauth_secrets = app.config.get("OAUTH_CLIENT_SECRETS_FILE")

    if not oauth_secrets:
        raise FileNotFoundError(f"OAuth client secrets not found at : {oauth_secrets}")
    
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Adapter + domain binders
    supabase_adapter = SupabaseAdapter(url=app.config["SUPABASE_URL"], key=app.config["SUPABASE_KEY"])
    supabase_file_adapter = SupabaseFileStorageAdapter(url=app.config["SUPABASE_URL"], key=app.config["SUPABASE_KEY"])

    binders = {
        "medical": BinderMedical(supabase_adapter),
        "business": BinderBusiness(supabase_adapter),
    }

    app.config.setdefault("BINDERS", binders)

    # Auth
    secrets = json.loads(oauth_secrets)
    client_id = secrets["web"]["client_id"]
    client_secret = secrets["web"]["client_secret"]

    google_client = oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    file_service = FileService(supabase_file_adapter)
    
    auth = AuthService(
        adapter=supabase_adapter,
        file_adapter=supabase_file_adapter,
        google_client=google_client,
        jwt_secret=jwt_secret,
        redirect_uri=app.config["OAUTH_REDIRECT_URI"]
    )

    auth_services = {
        "medical": auth,
        "business": auth,
    }


    # services/adapters
    payment_provider = StripePaymentProvider(app.config["STRIPE_API_KEY"])
    sub = SubscriptionService(supabase_adapter, payment_provider)
    subscription_services = {
        "medical": sub,
        "business": sub,
    }

    binder_services = {}
    for i in binders.keys():
        binder_services[i] = BinderService(binders[i]) 

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
        "binder_services": binder_services,
        "file_service" : file_service
    })

    app.extensions.setdefault("adapters", {})
    app.extensions["adapters"].update({
        "supabase_adapter": supabase_adapter,   
        "supabase_file_adapter": supabase_file_adapter,
    })

    return app


# --- WSGI entrypoint variable (used by PythonAnywhere / uWSGI) ---
# Creating `app` at module level is deliberate so WSGI can import it:
app = create_app()