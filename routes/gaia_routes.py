"""
gaia_routes.py
--------------
Dynamic endpoints for analytics and productivity metrics.
Uses the modular GaiaEngine to compute any registered metric.
"""

from flask import Blueprint, request, jsonify, current_app
from gaia import GaiaEngine
from utils.log_events import log_with_binder

gaia_blueprint = Blueprint("gaia", __name__)
gaia_engine = GaiaEngine()


def make_response(data=None, message="", status="success"):
    """
    Unified JSON response format.
    """
    return jsonify({
        "status": status,
        "data": data or {},
        "message": message
    })


@gaia_blueprint.route("/metrics", methods=["GET"])
def list_metrics():
    """
    List all available metric plugins in Gaia.

    Example:
        GET /api/gaia/metrics
    """
    metrics = gaia_engine.list_available_metrics()
    return make_response(metrics, "Available metrics retrieved.")


@gaia_blueprint.route("/compute", methods=["GET"])
def compute_metric():
    """
    Compute any registered Gaia metric dynamically.

    Example:
        GET /api/gaia/compute?metric=roi&domain=business&user_id=123&from=2025-01-01&to=2025-02-01

    Query Parameters:
        metric (str): Metric name (e.g., roi, finance, productivity)
        domain (str): Binder domain (e.g., medical, business)
        user_id (str): Current user identifier
        from (str): Optional start date
        to (str): Optional end date
        Other params: Passed to the metric compute() function
    """
    metric_name = request.args.get("metric")
    if not metric_name:
        return make_response({}, "Missing 'metric' parameter.", "error")

    domain = request.args.get("domain", "business")
    user_id = request.args.get("user_id")
    if not user_id:
        return make_response({}, "Missing 'user_id' parameter.", "error")

    # Retrieve binder (Medical or Business)
    binder = current_app.config["BINDERS"].get(domain)
    if not binder:
        return make_response({}, f"Unknown domain '{domain}'.", "error")

    # Set user context
    binder.current_user = user_id

    # Collect dynamic params for the metric
    params = {k: v for k, v in request.args.items() if k not in {"metric", "domain", "user_id"}}

    try:
        results = gaia_engine.compute(binder, metric_name, **params)
        log_with_binder(binder,301)
        return make_response(results, f"Metric '{metric_name}' computed successfully.") , 200
    except Exception as e:
        return make_response({}, f"Error computing metric '{metric_name}': {str(e)}", "error") , 400
