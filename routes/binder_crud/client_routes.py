from flask import Blueprint, current_app, request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import DEFAULT_DOMAIN, _get_domain_and_service, _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.log_events import log_event
from utils.make_res import make_response

client_blueprint = Blueprint("client", __name__)


# Error handlers for the blueprint
@client_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@client_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@client_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404


@client_blueprint.route("/clients", methods=["POST"])
def add_client():
    """
    Add a client (or patient) under the current user.

    Expected JSON:
    {
        "domain": "...",
        "user_id": "...",          # optional
        "client": { ... }
    }

    Returns: new client dict.
    """
    payload = request.get_json(force=True)
    if "client" not in payload:
        raise BadRequest("Missing 'client' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        
        service.set_current_user(payload["user_id"])

    client = service.create_client(payload["client"])
    client_id = client.get("id")

    log_event(service._binder,201 , metadata={"id" : client_id})
    return make_response(data=client, message="Client added successfully."), 201

@client_blueprint.route("/clients/<client_id>", methods=["GET"])
def get_client(client_id: str):
    """
    Retrieve a single client by id for the current user.

    Query param:
        domain (optional)
        user_id (optional)
    """
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    service = _get_domain_and_service({"domain": domain})

    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    if user_id:
        service.set_current_user(user_id)

    client = service.read_client(client_id)

    if not client:
        raise NotFound(f"Client {client_id} not found")
    session["client"]=client["id"]
    return make_response(data=client), 200

@client_blueprint.route("/clients/<client_id>", methods=["PATCH"])
def patch_client(client_id: str):
    """
    Update a client for the current user.

    Expected JSON:
    {
       "domain": "...",
       "user_id": "...",
       "patch": { ... }
    }
    """
    payload = request.get_json(force=True)
    if "patch" not in payload:
        raise BadRequest("Missing 'patch' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(payload["user_id"])

    service.update_client(client_id, payload["patch"])
    log_event(service._binder,401)
    return make_response(message="Client updated successfully."), 200

@client_blueprint.route("/clients/<client_id>", methods=["DELETE"])
def remove_client(client_id: str):
    """
    Delete a client for the current user.
    """
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)
    user_id = payload.get("user_id")
    
    if user_id:
        if not user_id == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(user_id)

    service.delete_client(client_id)
    return make_response(message="Client deleted."), 200

@client_blueprint.route("/client/search", methods=["POST"])
def client_search():
    """
    Unified search for clients endpoint. Backend decides strategy (number vs name vs fuzzy).
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
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(payload["user_id"])

    results = service.search_client(query)
    resp = make_response(data=results, message="Search completed.")
    resp.status_code = 200
    log_event(service._binder,300)
    return resp

@client_blueprint.route("/clients", methods=["GET"])
def list_clients():
    """
    List all clients for the current user.

    expected query params:
    domain (optional)
    user_id (optional)

    returns: list of client dicts
    """
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    service = _get_domain_and_service({"domain": domain})

    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    if user_id:
        service.set_current_user(user_id)

    clients = service.list_clients(
        start_at=int(request.args.get("start_at", 0)),
        limit=int(request.args.get("limit", 30))
    )
    return make_response(data={"clients": clients}, message="Clients retrieved successfully."), 200