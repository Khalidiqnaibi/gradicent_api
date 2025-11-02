"""
require_login.py
----------------
Decorator to require login for Flask routes.
"""
from flask import session, redirect

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return redirect("/logme")
        return function(*args, **kwargs)
    wrapper.__name__ = function.__name__  # force Flask to see the right name
    return wrapper