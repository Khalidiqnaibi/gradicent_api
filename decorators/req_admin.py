'''
require_admin.py
----------------
Decorator to require admin access for Flask routes.
'''

from flask import request, jsonify
from ..config import ADMIN_SECRET  


def admin_required(func):
    def wrapper(*args, **kwargs):
        key = request.args.get("key") or request.headers.get("X-Admin-Key")
        if key != ADMIN_SECRET:
            return jsonify({"error": "Unauthorized"}), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper