"""
require_login.py
----------------
Decorator to require login for Flask routes.
"""
from functools import wraps
from flask import request, current_app, jsonify, session , redirect
from auth.auth_service import AuthService
import sys

def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        domain = session.get("domain", session.get("binder", "business"))
        if len(args)>0 and args[0] in ["business","medical"] :
            domain = args[0]
            session["domain"] = domain
        elif "domain" in kwargs:
            domain = kwargs["domain"]
            session["domain"] = domain
        

        if session.get("plan") == "sec":
            user_id = session.get("user_id")
            if not user_id:
                return redirect("/login")

            auth_service: AuthService = current_app.extensions["services"][
                "auth_services"
            ].get(domain)

            user = auth_service.adapter.get_user(domain, user_id)
            

            request.current_user = user
            return fn(*args, **kwargs)

        # Normal auth path
        token = (
            request.headers.get("Authorization", "")
            .replace("Bearer ", "")
            or session.get("jwt")
        )

        auth_service: AuthService = current_app.extensions["services"][
            "auth_services"
        ].get(domain)

        user = auth_service.verify_token_and_get_user(domain, token)
        if not user:
            return redirect("/login")

        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper
