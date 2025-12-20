"""
require_login.py
----------------
Decorator to require login for Flask routes.
"""
from functools import wraps
from flask import request, current_app, jsonify, session , redirect
from auth.auth_service import AuthService

def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get('plan') == "sec":
            return fn(*args, **kwargs)
        domain = session.get("domain", session.get("binder", "business"))
        token = request.headers.get("Authorization", "").replace("Bearer ", "") or session.get("jwt")
        auth_service: AuthService = current_app.extensions["services"]["auth_services"].get(session.get("domain",session.get("binder","business")))
        user = auth_service.verify_token_and_get_user(domain,token)
        if not user:
            return redirect("/login") #jsonify({"status": "error", "message": "unauthenticated"}), 401
        # Attach user to request context for controllers
        request.current_user = user
        return fn(*args, **kwargs)
    return wrapper