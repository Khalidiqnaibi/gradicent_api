"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

import os
from flask import Flask ,request
from authlib.integrations.flask_client import OAuth
import json
import re

from flask_cors import CORS

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
from routes.file_routes import file_routes
from config import DefaultConfig
from services.binder_service import BinderService, BinderServiceError

def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(DefaultConfig())
    oauth = OAuth(app)

    BACKEND_URL = app.config.get("BACKEND_URL", "https://api.bindersoftware.com").split(".")[-2]

    @app.before_request
    def handle_options_preflight():
        """Instantly intercept and approve browser OPTIONS preflight requests."""
        if request.method == 'OPTIONS':
            response = app.make_response('')
            origin = request.headers.get('Origin')
            
            # Check if the requesting origin belongs to your domain context
            if origin and ('bindersoftware.com' in origin or 'localhost' in origin):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Refresh-Token'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
                response.headers['Access-Control-Max-Age'] = '86400'  # Cache preflight for 24 hours
            return response

    @app.after_request
    def append_cors_to_responses(response):
        """Append credentials and origin headers to standard responses automatically."""
        origin = request.headers.get('Origin')
        if origin and ('bindersoftware.com' in origin or 'localhost' in origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            # Prevent duplication issues if headers were already set
            if 'Access-Control-Allow-Headers' not in response.headers:
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Refresh-Token'
        return response

    app.config.update(
        SESSION_COOKIE_DOMAIN='.bindersoftware.com', 
        SESSION_COOKIE_SAMESITE='Lax', 
        SESSION_COOKIE_SECURE=True,      # Forces HTTPS transmission
        SESSION_COOKIE_HTTPONLY=True     # Safeguards cookie against XSS
    )
    app.secret_key = app.config.get("SECRET_KEY","supersecretkey")

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