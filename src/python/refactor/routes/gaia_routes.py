"""
gaia_routes.py
--------------
Endpoints for analytics and productivity metrics.
Relies on GaiaEngine, which consumes Binder data directly.
"""

from flask import Blueprint, request, jsonify, current_app
from ...binder import GaiaEngine
from datetime import datetime

gaia_blueprint = Blueprint("gaia", __name__)
gaia_engine = GaiaEngine()

def make_response(data=None, message="", status="success"):
    return jsonify({"status": status, "data": data, "message": message})


@gaia_blueprint.route("/analyze", methods=["GET"])
def analyze_data():
    """
    Compute high-level ROI and productivity metrics for a Binder user.
    """
    user_id = request.args.get("user_id")
    domain = request.args.get("domain", "business")
    start = request.args.get("from")
    end = request.args.get("to")

    binder = current_app.config["BINDERS"][domain]
    binder.set_current_user(user_id)

    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    results = gaia_engine.compute_roi(binder, start_dt, end_dt)
    return make_response(results, "ROI and productivity computed.")
