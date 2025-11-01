"""
app.py
------
Application entry point for Binder-based systems.
Initializes Flask, Firebase, and registers domain routes.
"""

from flask import Flask
from firebase_admin import credentials, initialize_app
from ..binder import FirebaseCrudAdapter,BinderMedical, BinderBusiness

# App & Firebase initialization
app = Flask(__name__)
app.secret_key = "CHANGE_THIS_KEY"

cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred, {"databaseURL": "https://your-project.firebaseio.com"})

# Adapter + domain binders
firebase_adapter = FirebaseCrudAdapter(root_path="users")

binders = {
    "medical": BinderMedical(firebase_adapter),
    "business": BinderBusiness(firebase_adapter),
}

# Route registration
from routes.gaia_routes import gaia_blueprint
from routes.binder_routes import binder_blueprint

app.register_blueprint(gaia_blueprint, url_prefix="/api/gaia")
app.register_blueprint(binder_blueprint, url_prefix="/api/binder")

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
