"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

import os
import firebase_admin
from flask import Flask
from firebase_admin import credentials, initialize_app

from config import DefaultConfig

from binder import (
    FirebaseCrudAdapter,
    BinderMedical,
    BinderBusiness,
    UnitedFirebaseAdapter,
)

from auth.auth_service import AuthService
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from payments.stripe_provider import StripePaymentProvider

from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint
from routes.payments_routes import payments_blueprint
from routes.auth_routes import auth_blueprint
from routes.frontend_routes import frontend_blueprint
from routes.file_routes import file_routes


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(config_name: str = "default") -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Load config
    app.config.from_object(DefaultConfig())

    # ---- SECURITY ----
    jwt_secret = app.config.get("JWT_SECRET") or app.config.get("SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError(
            "Missing JWT_SECRET or SECRET_KEY in app config for AuthService"
        )

    # ---- FIREBASE (INIT ONCE) ----
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            app.config["FIREBASE"]["credentials_path"]
        )
        initialize_app(
            cred,
            {
                "databaseURL": app.config["FIREBASE"]["databaseURL"],
                "storageBucket": app.config["FIREBASE"]["storageBucket"],
            },
        )

    # ---- ADAPTERS & BINDERS ----
    united_firebase_adapter = UnitedFirebaseAdapter(root_path="Gradicent")
    legacy_firebase_adapter_medical = FirebaseCrudAdapter(root_path="drs")

    binders = {
        "medical": BinderMedical(united_firebase_adapter),
        "business": BinderBusiness(united_firebase_adapter),
    }

    app.config.setdefault("BINDERS", binders)

    # ---- AUTH SERVICE ----
    google_config = {
        "client_secrets_path": app.config["OAUTH_CLIENT_SECRETS_FILE"],
        "redirect_uri": app.config["OAUTH_REDIRECT_URI"],
        "scopes": app.config.get(
            "OAUTH_SCOPES",
            ["openid", "email", "profile"],
        ),
    }

    auth = AuthService(
        adapter=united_firebase_adapter,
        legacy_adapter=legacy_firebase_adapter_medical,
        google_config=google_config,
        jwt_secret=jwt_secret,
    )

    auth_services = {
        "medical": auth,
        "business": auth,
    }

    # ---- PAYMENTS & SUBSCRIPTIONS ----
    payment_provider = StripePaymentProvider(
        app.config["STRIPE_API_KEY"]
    )

    subscription_service = SubscriptionService(
        united_firebase_adapter,
        payment_provider,
    )

    subscription_services = {
        "medical": subscription_service,
        "business": subscription_service,
    }

    # ---- ROUTES ----
    app.register_blueprint(
        gaia_blueprint,
        url_prefix=app.config["GAIA_ROUTE_PREFIX"],
    )
    app.register_blueprint(
        binder_blueprint,
        url_prefix=app.config["BINDER_ROUTE_PREFIX"],
    )
    app.register_blueprint(
        payments_blueprint,
        url_prefix=app.config["PAYMENT_ROUTE_PREFIX"],
    )
    app.register_blueprint(
        auth_blueprint,
        url_prefix=app.config["AUTH_ROUTE_PREFIX"],
    )
    app.register_blueprint(
        file_routes,
        url_prefix=app.config["FILE_ROUTE_PREFIX"],
    )
    app.register_blueprint(
        frontend_blueprint,
        url_prefix=app.config["FRONT_ROUTE_PREFIX"],
    )

    # ---- SERVICE REGISTRY ----
    app.extensions.setdefault("services", {})
    app.extensions["services"].update(
        {
            "auth_services": auth_services,
            "subscription_services": subscription_services,
            "payment_provider": payment_provider,
            "binders": binders,
        }
    )

    return app


# ---- WSGI ENTRYPOINT (IMPORTANT) ----
app = create_app()
