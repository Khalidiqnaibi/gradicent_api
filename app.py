"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

from flask import Flask
from firebase_admin import credentials, initialize_app
from BinderSoftware_api.services.subscription_service import SubscriptionService
from binder import FirebaseCrudAdapter,BinderMedical, BinderBusiness,UserRepository

from auth.auth_service import AuthService
from services.user_service import UserService
from payments.stripe_provider import StripePaymentProvider
from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint
from routes.payments_routes import payments_blueprint
from routes.auth_routes import auth_blueprint
import config

# App & Firebase initialization
app = Flask(__name__)
app.secret_key = "abcdefghijk123"

cred = credentials.Certificate(r"/home/RiaSoftware/s/key2.json")
initialize_app(cred, {
    'databaseURL': 'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/',
    'storageBucket': 'monydb-f2cdb.appspot.com'
})

CONFIG=config.DefaultConfig()


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(CONFIG)
    
    # Adapter + domain binders
    firebase_adapter_business = FirebaseCrudAdapter(root_path="business")
    firebase_adapter_medical = FirebaseCrudAdapter(root_path="drs")

    binders = {
        "medical": BinderMedical(firebase_adapter_medical),
        "business": BinderBusiness(firebase_adapter_business),
    }

    app.config.setdefault("BINDERS", binders)

    # services/adapters
    storage = FirebaseCrudAdapter(firebase_config=app.config['FIREBASE'])
    user_service = UserService(storage)
    payment_provider = StripePaymentProvider(CONFIG["STRIPE_API_KEY"])
    subscription_service = SubscriptionService(storage, payment_provider)

    dr_user_repository =UserRepository(firebase_adapter_medical)
    business_user_repository =UserRepository(firebase_adapter_business)

    # Auth
    auth_service = AuthService(client_secrets_path=app.config['GOOGLE_SECRETS'], redirect_uri=app.config['OAUTH_REDIRECT'])

    # register blueprints and pass factories via app extensions
    app.register_blueprint(gaia_blueprint, url_prefix='/api/gaia')
    app.register_blueprint(binder_blueprint, url_prefix='/api/binder')
    app.register_blueprint(payments_blueprint, url_prefix='/api/payments')
    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")

    # Attach services for controllers to pull from app context
    app.extensions.setdefault("services", {})
    app.extensions["services"].update({
        "user_service": user_service,
        "dr_user_repository": dr_user_repository,
        "business_user_repository":business_user_repository,
        "auth_service": auth_service,
        "subscription_service": subscription_service,
        "payment_provider": payment_provider,
        "binders": binders,
    })
    return app 

if __name__ == '__main__':
    create_app().run(host=CONFIG["HOST"], port=CONFIG["PORT"], debug=CONFIG["DEBUG"])
