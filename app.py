"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

import os
from flask import Flask ,request, session
from werkzeug.exceptions import HTTPException
from authlib.integrations.flask_client import OAuth
import json
import re
from datetime import timedelta
from urllib.parse import urlsplit

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

from routes.binder_crud.client_routes import client_blueprint
from routes.binder_crud.service_routes import service_blueprint
from routes.binder_crud.interaction_routes import interaction_blueprint
from routes.binder_crud.product_routes import product_blueprint
from routes.binder_crud.transaction_routes import transaction_blueprint
from routes.binder_crud.appointment_routes import appointment_blueprint
from routes.binder_crud.employee_routes import employee_blueprint
from routes.binder_crud.user_routes import user_blueprint

from config import DefaultConfig
from utils.make_res import make_response
from services.binder_service import BinderService, BinderServiceError

def _document_store(app: Flask, fallback):
    """
    Patient/client documents live in Firebase (Storage + the Firestore "gradicent files" collection)
    when FIREBASE_SERVICE_ACCOUNT holds a service-account key (JSON); otherwise in Supabase Storage.
    """
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if not raw:
        app.logger.warning("FIREBASE_SERVICE_ACCOUNT not set: documents are stored in Supabase Storage")
        return fallback
    import firebase_admin
    from firebase_admin import credentials
    from binder.adapters.firebase_document_store import FirebaseDocumentStore

    info = json.loads(raw)
    bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip() or f"{info['project_id']}.appspot.com"
    try:
        fb_app = firebase_admin.get_app("documents")
    except ValueError:
        fb_app = firebase_admin.initialize_app(
            credentials.Certificate(info), {"storageBucket": bucket, "projectId": info["project_id"]}, name="documents",
        )
    return FirebaseDocumentStore(fb_app, collection=os.getenv("FIREBASE_FILES_COLLECTION", "gradicent files"))


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(DefaultConfig())
    oauth = OAuth(app)

    def _allowed_origin(origin):
        """Our own frontends only: https://bindersoftware.com and its subdomains, or local development."""
        if not origin:
            return False
        parts = urlsplit(origin)
        host = (parts.hostname or "").lower()
        if parts.scheme == "https" and (host == "bindersoftware.com" or host.endswith(".bindersoftware.com")):
            return True
        return parts.scheme in ("http", "https") and host in ("localhost", "127.0.0.1")

    @app.before_request
    def handle_options_preflight():
        """Instantly intercept and approve browser OPTIONS preflight requests."""
        if request.method == 'OPTIONS':
            response = app.make_response('')
            origin = request.headers.get('Origin')
            
            # Check if the requesting origin belongs to your domain context
            if _allowed_origin(origin):
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
        if _allowed_origin(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            # Prevent duplication issues if headers were already set
            if 'Access-Control-Allow-Headers' not in response.headers:
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Refresh-Token'
            response.headers['Vary'] = 'Origin'
        # Responses carry patient and client records: never let browsers or proxies cache them
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        """Return JSON (not HTML) for 4xx/5xx raised by Flask/werkzeug, e.g. unknown routes."""
        return make_response(message=err.description or err.name, status="error", code=err.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        """
        Last-resort handler: without it an unhandled exception escapes the serverless function
        (FUNCTION_INVOCATION_FAILED), which also drops the CORS headers so browsers report a
        CORS error instead of the real failure.
        """
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        return make_response(message="Internal server error", status="error", code=500)

    app.config.update(
        SESSION_COOKIE_DOMAIN='.bindersoftware.com', 
        SESSION_COOKIE_SAMESITE='Lax', 
        SESSION_COOKIE_SECURE=True,      # Forces HTTPS transmission
        SESSION_COOKIE_HTTPONLY=True,    # Safeguards cookie against XSS
        PERMANENT_SESSION_LIFETIME=timedelta(days=app.config.get("SESSION_LIFETIME_DAYS", 7)),
        # Files go straight to storage, so API bodies are small JSON
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )

    # Ensure there's a JWT secret available for AuthService
    jwt_secret = app.config.get("JWT_SECRET") or app.config.get("SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("Missing JWT_SECRET or SECRET_KEY in app config for AuthService")
    # Session cookies must be signed with a real secret, never a well-known fallback
    app.secret_key = app.config.get("SECRET_KEY") or jwt_secret

    # Resolve credential and oauth secret file paths robustly
    oauth_secrets = app.config.get("OAUTH_CLIENT_SECRETS_FILE")

    if not oauth_secrets:
        raise FileNotFoundError(f"OAuth client secrets not found at : {oauth_secrets}")
    
    if app.config.get("DEBUG"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # plain-http OAuth for local development only

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

    file_service = FileService(_document_store(app, supabase_file_adapter))
    
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

    # Binder CRUD routes all act on a user's own records: require a signed-in session up front so
    # signed-out calls get a clean 401 instead of running queries without an owner.
    crud_blueprint_names = {
        bp.name for bp in (
            client_blueprint, service_blueprint, interaction_blueprint, product_blueprint,
            transaction_blueprint, appointment_blueprint, employee_blueprint, user_blueprint,
        )
    }

    @app.before_request
    def require_signed_in_user():
        if request.method == "OPTIONS" or request.blueprint not in crud_blueprint_names:
            return None
        if not session.get("user_id"):
            return make_response(status="error", message="unauthenticated", code=401)
        return None

    # register blueprints and pass factories via app extensions
    app.register_blueprint(gaia_blueprint, url_prefix=app.config["GAIA_ROUTE_PREFIX"])
    app.register_blueprint(binder_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(payments_blueprint, url_prefix=app.config["PAYMENT_ROUTE_PREFIX"])
    app.register_blueprint(auth_blueprint, url_prefix=app.config["AUTH_ROUTE_PREFIX"])
    app.register_blueprint(file_routes, url_prefix=app.config["FILE_ROUTE_PREFIX"])

    app.register_blueprint(client_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(service_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(interaction_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(product_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(transaction_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(appointment_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(employee_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])
    app.register_blueprint(user_blueprint, url_prefix=app.config["BINDER_ROUTE_PREFIX"])

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