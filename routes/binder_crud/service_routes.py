
from flask import current_app, request, session , Blueprint
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.make_res import make_response
from utils.log_events import log_event

service_blueprint = Blueprint("service_routes", __name__)


# Error handlers for the blueprint
@service_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@service_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@service_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404


@service_blueprint.route("/services", methods=["POST"])
def create_service():
    """
    Create a service offering.

    Input JSON:
        {
            "domain": str,
            "user_id": str,
            "service": dict
        }

    Returns:
        JSON envelope containing created service.
    """
    payload = request.get_json(force=True)
    if "service" not in payload:
        raise BadRequest("Missing 'service' payload")

    service = _get_domain_and_service(payload)
    if payload.get("user_id"):
        service.set_current_user(payload["user_id"])
        
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    svc = service.create_service(payload["service"])
    log_event(service._binder, 205)

    return make_response(data=svc, message="Service created successfully."), 201

@service_blueprint.route("/services/<service_id>", methods=["GET"])
def read_service(service_id: str):
    """
    Read a service offering.

    Query Params:
        domain (str)
        user_id (str)

    Returns:
        JSON envelope containing service data.
    """
    payload = {
        "domain": request.args.get("domain"),
        "user_id": request.args.get("user_id"),
    }

    service = _get_domain_and_service(payload)
    if payload.get("user_id"):
        service.set_current_user(payload["user_id"])
        
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    svc = service.read_service(service_id)
    if not svc:
        raise NotFound(f"Service {service_id} not found")

    return make_response(data=svc), 200

@service_blueprint.route("/services/<service_id>", methods=["PATCH"])
def update_service(service_id: str):
    """
    Update a service offering.

    Input JSON:
        {
            "domain": str,
            "user_id": str,
            "patch": dict
        }

    Returns:
        JSON envelope with status message.
    """
    payload = request.get_json(force=True)
    if "patch" not in payload:
        raise BadRequest("Missing 'patch' payload")

    service = _get_domain_and_service(payload)
    if payload.get("user_id"):
        service.set_current_user(payload["user_id"])
    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    service.update_service(service_id, payload["patch"])
    log_event(service._binder, 405)

    return make_response(message="Service updated successfully."), 200

@service_blueprint.route("/services/<service_id>", methods=["DELETE"])
def delete_service(service_id: str):
    """
    Delete a service offering.

    Input JSON (optional):
        {
            "domain": str,
            "user_id": str
        }

    Returns:
        JSON envelope with status message.
    """
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)

    if payload.get("user_id"):
        service.set_current_user(payload["user_id"])
        
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    service.delete_service(service_id)

    return make_response(message="Service deleted successfully."), 200

@service_blueprint.route("/services/search", methods=["POST"])
def service_search():
    """
    Unified search for service endpoint.
    Request JSON:
      { "domain": "...", "user_id": "...", "query": "..." }
    Response:
      { status, data: { results: [...] }, message }
    """
    payload = request.get_json(force=True, silent=True) or {}
    query = payload.get("query", "")
    if not query:
        raise BadRequest("Missing 'query' in request body")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        service.set_current_user(payload["user_id"])

    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    results = service.search_service(query)
    resp = make_response(data=results, message="Search completed.")
    resp.status_code = 200
    log_event(service._binder, 300)
    return resp

@service_blueprint.route("/services", methods=["GET"])
def list_services():
    """ 
    List services for current user.
    
    args:
        domain (str): Domain name (query param)
        user_id (str): User identifier (query param)
        start_at (int): Index to start the page from (query param)
        limit (int): max items to return (query param)

    returns:
        { status, data: { services: [...] }, message }

    """

    domain = request.args.get("domain")
    user_id = request.args.get("user_id")
    try:
        start_at = int(request.args.get("start_at", 0))
        limit = int(request.args.get("limit", 30))
    except ValueError:
        raise BadRequest("start_at and limit must be integers")

    service = _get_domain_and_service({"domain": domain, "user_id": user_id})
    if user_id:
        service.set_current_user(user_id)

    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    services = service.list_services(start_at, limit)
    return make_response(data={"services": services}, message="Services retrieved successfully."), 200