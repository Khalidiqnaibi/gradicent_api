'''
make_res.py
-----------
helper to unify responsies
'''
from flask import jsonify
from typing import Optional,Any

def make_response(data: Optional[Any] = None, message: str = "", status: str = "success", code: int = 200):
    """
    Build a standardized JSON response and HTTP code.

    Returns:
        (flask.Response, int): JSON response and HTTP status code.
    """
    payload = {"status": status, "data": data, "message": message}
    return jsonify(payload), code