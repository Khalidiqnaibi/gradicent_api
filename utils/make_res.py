'''
make_res.py
-----------
helper to unify responsies
'''
from flask import jsonify

def make_response(data=None, message="", status="success"):
    return jsonify({"status": status, "data": data, "message": message})