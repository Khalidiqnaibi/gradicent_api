'''
config.py
----------------
Configuration settings for Gradicent_api
'''

import os


ADMIN_SECRET = os.getenv("ADMIN_SECRET","bindersoftware.com")

# prices
STARTER_PRICE = os.getenv("STARTER_PRICE","5")
PRO_PRICE = os.getenv("PRO_PRICE","25")
ULTRA_PRICE = os.getenv("ULTRA_PRICE","125")
PACKAGE_PRICE = os.getenv("PACKAGE_PRICE","1000")
PLANS = {
    "starter": float(STARTER_PRICE),
    "pro": float(PRO_PRICE),
    "ultra": float(ULTRA_PRICE),
    "package": float(PACKAGE_PRICE),
}

# payment providers
PADDLE_VENDOR_ID = os.getenv("PADDLE_VENDOR_ID","")
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY","")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID","")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET","")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY","")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET","")

# other settings
FRONTEND_URL = os.getenv("FRONTEND_URL","http://localhost:3000")
DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./test.db")
LOG_LEVEL = os.getenv("LOG_LEVEL","DEBUG")
DEBUG = os.getenv("DEBUG","True").lower() in ("true", "1", "t")
PORT = int(os.getenv("PORT","5000"))
HOST = os.getenv("HOST","localhost")
SECRET_KEY = os.getenv("SECRET_KEY","supersecretkey")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME","binder_session")
SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS","7"))
USE_HTTPS = os.getenv("USE_HTTPS","False").lower() in ("true", "1", "t")

# OAuth settings
OAUTH_CLIENT_SECRETS_FILE = os.getenv("OAUTH_CLIENT_SECRETS_FILE","client_secrets.json")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI","http://localhost:5000/api/auth/callback")
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", str(60*60*24*30)))

# Firebase settings
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH",r"C:\Users\pc\Documents\GitHub\BinderSoftware_api\key2.json")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL",'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/')
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET",'monydb-f2cdb.appspot.com')

# route prefixes
API_PREFIX = "/api"
AUTH_ROUTE_PREFIX = f"{API_PREFIX}/auth"
PAYMENT_ROUTE_PREFIX = f"{API_PREFIX}/payments"
GAIA_ROUTE_PREFIX = f"{API_PREFIX}/gaia"
BINDER_ROUTE_PREFIX =f'{API_PREFIX}/binder'
FRONT_ROUTE_PREFIX = f''

class DefaultConfig:
    ADMIN_SECRET = ADMIN_SECRET
    STARTER_PRICE = STARTER_PRICE
    PRO_PRICE = PRO_PRICE
    ULTRA_PRICE = ULTRA_PRICE
    PACKAGE_PRICE = PACKAGE_PRICE
    PLANS = PLANS

    PADDLE_VENDOR_ID = PADDLE_VENDOR_ID
    PADDLE_API_KEY = PADDLE_API_KEY
    PAYPAL_CLIENT_ID = PAYPAL_CLIENT_ID
    PAYPAL_SECRET = PAYPAL_SECRET
    STRIPE_API_KEY = STRIPE_API_KEY
    STRIPE_WEBHOOK_SECRET = STRIPE_WEBHOOK_SECRET

    FRONTEND_URL = FRONTEND_URL
    DATABASE_URL = DATABASE_URL
    LOG_LEVEL = LOG_LEVEL
    DEBUG = DEBUG
    PORT = PORT
    HOST = HOST
    SECRET_KEY = SECRET_KEY
    SESSION_COOKIE_NAME = SESSION_COOKIE_NAME
    SESSION_LIFETIME_DAYS = SESSION_LIFETIME_DAYS
    USE_HTTPS = USE_HTTPS

    OAUTH_CLIENT_SECRETS_FILE = OAUTH_CLIENT_SECRETS_FILE
    OAUTH_REDIRECT_URI = OAUTH_REDIRECT_URI
    OAUTH_SCOPES = OAUTH_SCOPES

    ACCESS_TOKEN_TTL_SECONDS = ACCESS_TOKEN_TTL_SECONDS
    REFRESH_TOKEN_TTL_SECONDS = REFRESH_TOKEN_TTL_SECONDS

    FIREBASE = {
        "credentials_path": FIREBASE_CREDENTIALS_PATH,
        "databaseURL": FIREBASE_DATABASE_URL,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
    }

    API_PREFIX = API_PREFIX
    AUTH_ROUTE_PREFIX = AUTH_ROUTE_PREFIX
    GAIA_ROUTE_PREFIX = GAIA_ROUTE_PREFIX
    PAYMENT_ROUTE_PREFIX = PAYMENT_ROUTE_PREFIX
    BINDER_ROUTE_PREFIX = BINDER_ROUTE_PREFIX
    FRONT_ROUTE_PREFIX = FRONT_ROUTE_PREFIX
