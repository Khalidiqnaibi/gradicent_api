
from flask import Blueprint, current_app, request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import DEFAULT_DOMAIN, _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.log_events import log_event
from utils.make_res import make_response

interaction_blueprint = Blueprint("interaction", __name__)


# Error handlers for the blueprint
@interaction_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error", code=400)

@interaction_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error", code=400)

@interaction_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error", code=404)


@interaction_blueprint.route("/clients/<client_id>/interactions", methods=["POST"])
def add_interaction(client_id: str):
    """
    Add an interaction (or visit) for a client.

    Expected JSON:
    {
       "domain":"medical" | "business",
       "user_id":"...",
       "interaction": { ... }
    }
    """
    payload = request.get_json(force=True)
    if "interaction" not in payload:
        raise BadRequest("Missing 'interaction' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action", code=401)
        service.set_current_user(payload["user_id"])

    if int(client_id) < 0:
        client_id = session["client_id"]

    interaction = service.create_interaction(client_id, payload["interaction"])

    interaction_no = payload["interaction"].get("vno",payload["interaction"].get("interaction_no")) 

    interaction_no = interaction_no-1 or 0

    log_event(service._binder,202,metadata={"id" : client_id , "interaction_no":interaction_no})
    return make_response(data=interaction, message="Interaction created.", code=201)

@interaction_blueprint.route("/clients/<client_id>/interactions", methods=["GET"])
def list_interactions(client_id: str):
    """
    List interactions (or visits) for a client with pagination.

    Expects:
        client_id (str): The target client/patient ID.
        domain (str, optional): Passed via query params.
        user_id (str, optional): Passed via query params.
        start_at (int, optional): The starting index for pagination (default 0).
        limit (int, optional): The number of records to return (default 10).

    Returns:
        JSON: {status: "success", data: list[Dict], message: "Got Interactions."}
    """
    domain = request.args.get("domain", session.get("domain", DEFAULT_DOMAIN))
    user_id = request.args.get("user_id", session.get("user_id"))
    
    start_at = int(request.args.get("start_at", 0))
    limit = int(request.args.get("limit", 30))
    
    service = _get_domain_and_service({"domain": domain})
    if user_id:
        if not user_id == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action", code=401)
        service.set_current_user(user_id)

    interactions = service.list_interactions(
        client_id=client_id, 
        start_at=start_at, 
        limit=limit
    )
    
    return make_response(data=interactions, message=f"{limit} Interactions retrieved.", code=200)

@interaction_blueprint.route("/clients/<client_id>/interactions/<int:interaction_no>", methods=["GET"])
def get_interaction(client_id: str, interaction_no: int):
    """
    Retrieve a specific interaction by its index/number.

    Expects:
        client_id (str): The target client/patient ID.
        interaction_no (int): The specific interaction index.
        domain (str, optional): Query param.

    Returns:
        JSON: {status: "success", data: Dict, message: "Interaction retrieved."}
    """
    domain = request.args.get("domain", session.get("domain", DEFAULT_DOMAIN))
    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(session.get("user_id"))

    # Service logic typically uses 0-based indexing
    idx = interaction_no - 1 if interaction_no > 0 else 0
    
    interaction = service.read_interaction(client_id=client_id, interaction_no=idx)
    if not interaction:
        raise NotFound(f"Interaction {interaction_no} not found for client {client_id}")

    return make_response(data=interaction, message="Interaction retrieved.", code=200)

@interaction_blueprint.route("/clients/<client_id>/interactions", methods=["PATCH"])
def update_interaction(client_id: str):
    """
    Update interaction (or visit) for a client.

    Expected JSON:
    {
       "domain" (str): "...",
       "user_id" (str): "...",
       "interaction_no (int):"...",
       "patch" (list[Any]): { ... }
    }
    """
    payload = request.get_json(force=True)
    if "patch" not in payload:
        raise BadRequest("Missing 'patch' payload")
    
    if "interaction_no" not in payload:
        raise BadRequest("Missing 'interaction_no' payload")

    service = _get_domain_and_service(payload)
    service.set_current_user(session["user_id"])
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action", code=401)
        service.set_current_user(payload["user_id"])
    
    if  int(client_id) < 0:
        client_id = session["client_id"]

    interaction_no = int(payload["interaction_no"])- 1
    if not interaction_no > 0 :
        interaction_no = 0

    service.update_interactions(client_id=client_id,interaction_no=interaction_no,patch = payload["patch"])

    log_event(service._binder,402,metadata={"id" : client_id , "interaction_no":interaction_no})
    return make_response(data=payload, message="Updated Interactions.", code=201)

@interaction_blueprint.route("/clients/<client_id>/interactions", methods=["DELETE"])
def delete_interaction(client_id: str):
    """
    Delete interaction (or visit) for a client.

    Expected JSON:
    {
       "domain" (str): "...",
       "interaction_no (int):"...",
       "user_id" (str): "..."
    }
    """
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)
    interaction_no = payload.get("interaction_no")
    user_id = payload.get("user_id")
    if user_id:
        if not user_id == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action", code=401)
        service.set_current_user(user_id)
    
    if not interaction_no:
        raise BadRequest("'interaction_no' not found in payload")

    service.delete_interactions(client_id=client_id , interaction_no = interaction_no)
    return make_response(data=payload, message="Deleted Interactions.", code=201)
    