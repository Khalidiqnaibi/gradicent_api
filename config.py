'''
config.py
----------------
Configuration settings for Gradicent_api
'''

import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_SECRET = os.getenv("ADMIN_SECRET")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# EVENTS
EVENTS={
    100:"logged in",
    101:"printed client data",
    102:"printed client interacion data",

    200:"user added",
    201:"client added" ,
    202:"interaction added",
    203:"file uploaded",
    204:"product added",
    205:"service added",
    206:"employee added",
    207: "transaction added",

    300:"search done",
    301:"analytics shown",
    303:"gde used",

    400:"user updated",
    401:"client updated",
    402:"interaction updated",
    403:"file updated",
    404:"product updated",
    405:"service updated",
    406:"employee updated",
    407:"transaction updated",
    
    500:"fooled",

    600:"first payment done",
    601:"payment done",
    602:"product purchased",
    603:"service purchased",
    604:"employee paid"
}

# prices
STARTER_PRICE = os.getenv("STARTER_PRICE",5)
PRO_PRICE = os.getenv("PRO_PRICE",25)
ULTRA_PRICE = os.getenv("ULTRA_PRICE",125)
PACKAGE_PRICE = os.getenv("PACKAGE_PRICE",1000)
PLANS = {
    "starter": {
        "key": "starter",
        "name": "Starter",
        "badge": "Great for solo",
        "description": "Core client management and light reporting for new teams.",
        "price": float(STARTER_PRICE),
        "featured": False,
        "features": [
            "Client and contact tracking",
            "Basic analytics dashboards",
            "Email support"
        ]
    },
    "pro": {
        "key": "pro",
        "name": "Pro",
        "badge": "Most popular",
        "description": "Automation-ready workflows with deeper reporting insights.",
        "price": float(PRO_PRICE),
        "featured": True,
        "features": [
            "Advanced analytics views",
            "Team collaboration tools",
            "Priority support"
        ]
    },
    "ultra": {
        "key": "ultra",
        "name": "Ultra",
        "badge": "Enterprise",
        "description": "Full-featured platform with advanced automation and insights.",
        "price": float(ULTRA_PRICE),
        "featured": False,
        "features": [
            "Custom integrations",
            "Dedicated account manager",
            "24/7 phone support"
        ]
    },
    "package": {
        "key": "package",
        "name": "Package",
        "badge": "Custom",
        "description": "Tailored solution for large organizations with unique needs.",
        "price": float(PACKAGE_PRICE),
        "featured": False,
        "features": [
            "White-label options",
            "On-premise deployment",
            "SLA guarantees"
        ]
    }
}

# payment providers
PADDLE_VENDOR_ID = os.getenv("PADDLE_VENDOR_ID","")
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY","")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID","")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET","")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY","")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET","")

# other settings
BACKEND_URL= os.getenv("BACKEND_URL")
FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./test.db")
LOG_LEVEL = os.getenv("LOG_LEVEL","DEBUG")
DEBUG = os.getenv("DEBUG","True").lower() in ("true", "1", "t")
PORT = int(os.getenv("PORT","5000"))
HOST = os.getenv("HOST","localhost")
SECRET_KEY = os.getenv("SECRET_KEY")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME")
SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS","7"))
USE_HTTPS = os.getenv("USE_HTTPS","False").lower() in ("true", "1", "t")

# OAuth settings
OAUTH_CLIENT_SECRETS_FILE = os.getenv("OAUTH_CLIENT_SECRET_JSON")
OAUTH_GOOGLE_CLIENT_ID = os.getenv("OAUTH_GOOGLE_CLIENT_ID")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", str(60*60*24*30)))

# supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# route prefixes
API_PREFIX = "/api"
AUTH_ROUTE_PREFIX = f"{API_PREFIX}/auth"
PAYMENT_ROUTE_PREFIX = f"{API_PREFIX}/payments"
GAIA_ROUTE_PREFIX = f"{API_PREFIX}/gaia"
BINDER_ROUTE_PREFIX =f'{API_PREFIX}/binder'
FILE_ROUTE_PREFIX = f'{API_PREFIX}/binder/files'
FRONT_ROUTE_PREFIX = f''

# binder
MIN_SEC_REC = 15

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

    BACKEND_URL = BACKEND_URL
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
    OAUTH_GOOGLE_CLIENT_ID = OAUTH_GOOGLE_CLIENT_ID
    OAUTH_SCOPES = OAUTH_SCOPES

    ACCESS_TOKEN_TTL_SECONDS = ACCESS_TOKEN_TTL_SECONDS
    REFRESH_TOKEN_TTL_SECONDS = REFRESH_TOKEN_TTL_SECONDS

    MIN_SEC_REC = MIN_SEC_REC

    SUPABASE_KEY = SUPABASE_KEY
    SUPABASE_URL = SUPABASE_URL

    API_PREFIX = API_PREFIX
    AUTH_ROUTE_PREFIX = AUTH_ROUTE_PREFIX
    GAIA_ROUTE_PREFIX = GAIA_ROUTE_PREFIX
    PAYMENT_ROUTE_PREFIX = PAYMENT_ROUTE_PREFIX
    BINDER_ROUTE_PREFIX = BINDER_ROUTE_PREFIX
    FILE_ROUTE_PREFIX = FILE_ROUTE_PREFIX
    FRONT_ROUTE_PREFIX = FRONT_ROUTE_PREFIX
