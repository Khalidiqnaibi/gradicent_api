"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

from flask import Flask
from firebase_admin import credentials, initialize_app
from binder import FirebaseCrudAdapter,BinderMedical, BinderBusiness

# App & Firebase initialization
app = Flask(__name__)
app.secret_key = "abcdefghijk123"

cred = credentials.Certificate(r"/home/RiaSoftware/s/key2.json")
initialize_app(cred, {
    'databaseURL': 'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/',
    'storageBucket': 'monydb-f2cdb.appspot.com'
})

# Adapter + domain binders
firebase_adapter_business = FirebaseCrudAdapter(root_path="business")
firebase_adapter_medical = FirebaseCrudAdapter(root_path="drs")

binders = {
    "medical": BinderMedical(firebase_adapter_medical),
    "business": BinderBusiness(firebase_adapter_business),
}

# Route registration
from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint

app.register_blueprint(gaia_blueprint, url_prefix="/api/gaia")
app.register_blueprint(binder_blueprint, url_prefix="/api/binder")

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
