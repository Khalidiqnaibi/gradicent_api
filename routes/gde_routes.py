"""
gde_routes.py
-------------
API routes for Gradicent Decision Engine.
"""

from flask import Blueprint, request, jsonify, current_app
from services.gde_service import analyze_business_decisions

gde_blueprint = Blueprint("gde", __name__)



@gde_blueprint.route("/analyze", methods=["GET"])
def analyze():
    user_id = request.args.get("user_id")
    domain = request.args.get("domain", "business")

    if not user_id:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "Missing user_id"
        }), 400

    binder = current_app.config["BINDERS"].get(domain)
    if not binder:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "Invalid domain"
        }), 400

    binder.current_user = user_id
    result = analyze_business_decisions(binder)

    return jsonify({
        "status": "success",
        "data": result,
        "message": "Decision analysis completed"
    })
