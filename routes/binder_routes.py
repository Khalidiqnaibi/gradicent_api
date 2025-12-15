"""
binder_routes.py
----------------
Flask Blueprint exposing Binder endpoints.

Responsibilities:
- Accept HTTP requests, validate inputs, and return uniform JSON responses.
- Delegate domain operations to BinderService (thin controllers).
- Provide consistent error handling and logging.

Design notes:
- Controller only validates + delegates (single responsibility).
- All handlers are <= ~30 lines.
- Uses explicit return values and typed signatures.
"""

import requests
from typing import Any, Dict, Optional
from flask import Blueprint, request, jsonify, current_app , session
from werkzeug.exceptions import BadRequest, NotFound

from services.binder_service import BinderService, BinderServiceError
from services.appointments_service import AppointmentsService
from utils.get_appointments import get_appointments
from utils.get_plan_status import get_plan_status, get_plan_data
from config import BACKEND_URL

binder_blueprint = Blueprint("binder", __name__)

# Constants
DEFAULT_DOMAIN = "business"

# Helpers
def make_response(data: Any = None, message: str = "", status: str = "success"):
    """
    Build uniform API response.

    Returns:
        flask.Response: JSON response with standard envelope.
    """
    return jsonify({"status": status, "data": data, "message": message})

def _get_domain_and_service(payload: Dict[str, Any]) -> BinderService:
    """
    Resolve domain from payload and return a BinderService that wraps the configured binder.

    Raises:
        BadRequest: if domain is missing or binder not configured.
    """
    domain = payload.get("domain", DEFAULT_DOMAIN)
    binders = current_app.config.get("BINDERS", {})
    binder_impl = binders.get(domain)
    if not binder_impl:
        current_app.logger.error("Binder not configured for domain: %s", domain)
        raise BadRequest(f"Unknown domain: {domain}")
    return BinderService(binder_impl)

# Error handlers for the blueprint
@binder_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@binder_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@binder_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404

# Routes (thin controllers)

@binder_blueprint.route("/get_plan_status",methods=["GET"])
def get_plan_status():
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    payload ={
        "domain": domain
    }
    service = _get_domain_and_service(payload)

    plan , first  = get_plan_data(service=service)
    
    status ,days = get_plan_status(plan,first)

    result = {
        "days": days,
        "status":status,
        "plan": plan
    }
    return make_response(data=result) , 200

@binder_blueprint.route("/get_domain",methods=["GET"])
def get_domain():
    domain = session.get("domain", session.get("binder", "business"))
    return make_response(data=domain) , 200

@binder_blueprint.route("/create_user", methods=["POST"])
def create_user():
    """
    Create a user in the selected Binder domain.

    Expected JSON:
    {
        "domain": "business" | "medical",
        "user": { "id": "...", ... }
    }

    Returns:
        {status, data: user, message}
    """
    payload = request.get_json(force=True)
    if "user" not in payload:
        raise BadRequest("Missing 'user' payload")

    service = _get_domain_and_service(payload)
    user = service.create_user(payload["user"])
    return make_response(data=user, message="User created successfully."), 201

@binder_blueprint.route("/set_current_user", methods=["POST"])
def set_current_user():
    """
    Set the current user for subsequent operations (stateless convenience).

    Expected JSON:
    {
        "domain": "...",
        "user_id": "..."
    }
    """
    payload = request.get_json(force=True)
    if "user_id" not in payload:
        raise BadRequest("Missing 'user_id'")

    service = _get_domain_and_service(payload)
    service.set_current_user(payload["user_id"])
    return make_response(message="Current user set."), 200

@binder_blueprint.route("/clients", methods=["POST"])
def add_client():
    """
    Add a client (or patient) under the current user.

    Expected JSON:
    {
        "domain": "...",
        "user_id": "...",          # optional if session / token used
        "client": { ... }
    }

    Returns: new client dict.
    """
    payload = request.get_json(force=True)
    if "client" not in payload:
        raise BadRequest("Missing 'client' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        service.set_current_user(payload["user_id"])

    client = service.create_client(payload["client"])
    return make_response(data=client, message="Client added successfully."), 201

@binder_blueprint.route("/clients/<client_id>", methods=["GET"])
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
    if user_id:
        service.set_current_user(user_id)

    client = service.read_client(client_id)
    session["client"]=client["id"]
    if client is None:
        raise NotFound(f"Client {client_id} not found")
    return make_response(data=client), 200

@binder_blueprint.route("/clients/<client_id>", methods=["PATCH"])
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
        service.set_current_user(payload["user_id"])

    service.update_client(client_id, payload["patch"])
    return make_response(message="Client updated successfully."), 200



@binder_blueprint.route("/clients/<client_id>", methods=["DELETE"])
def remove_client(client_id: str):
    """
    Delete a client for the current user.
    """
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)
    user_id = payload.get("user_id")
    if user_id:
        service.set_current_user(user_id)

    service.delete_client(client_id)
    return make_response(message="Client deleted."), 200

@binder_blueprint.route("/search/client", methods=["POST"])
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
        service.set_current_user(payload["user_id"])

    results = service.search_client(query)
    resp = make_response(data=results, message="Search completed.")
    resp.status_code = 200
    return resp

# Example nested resource: create interaction / visit
@binder_blueprint.route("/clients/<client_id>/interactions", methods=["POST"])
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
        service.set_current_user(payload["user_id"])

    interaction = service.create_interaction(client_id, payload["interaction"])
    return make_response(data=interaction, message="Interaction created."), 201

@binder_blueprint.route("/clients/<client_id>/interactions", methods=["GET"])
def list_interaction(client_id: str):
    """
    List interactions (or visits) for a client.

    Query param:
        domain (optional)
        user_id (optional)
    """
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    service = _get_domain_and_service({"domain": domain})
    if user_id:
        service.set_current_user(user_id)

    interactions = service.list_interactions(client_id=client_id)
    return make_response(data=interactions, message="Got Interactions."), 201

@binder_blueprint.route("/clients/<client_id>/interactions", methods=["PATCH"])
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
    if "user_id" in payload:
        service.set_current_user(payload["user_id"])

    service.update_interactions(client_id=client_id,interaction_no=payload["interaction_no"],patch = payload["patch"])
    return make_response(data=payload, message="Updated Interactions."), 201

@binder_blueprint.route("/clients/<client_id>/interactions", methods=["DELETE"])
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
        service.set_current_user(user_id)
    
    if not interaction_no:
        raise BadRequest("'interaction_no' not found in payload")

    service.delete_interactions(client_id=client_id , interaction_no = interaction_no)
    return make_response(data=payload, message="Deleted Interactions."), 201

@binder_blueprint.route("/appointments/<date>", methods=["GET"])
def get_appointments_for_date(date):
    """
    Read appointments for a given date.
    
    Requires:
        domain
        user_id
    """
    payload = {
        "domain": request.args.get("domain", DEFAULT_DOMAIN),
        "user_id": request.args.get("user_id")
    }

    if not payload["user_id"]:
        raise BadRequest("Missing user_id")

    service = _get_domain_and_service(payload)
    service.set_current_user(payload["user_id"])

    result = service.get_appointments(date)
    return make_response(data={"appointments": result}), 200

@binder_blueprint.route("/appointments/<date>", methods=["PATCH"])
def save_appointments_for_date(date):
    """
    Save or replace appointments for the given date.
    Body:
        { "appointments": [...] }
    """
    payload = request.get_json(force=True)
    if "appointments" not in payload:
        raise BadRequest("Missing appointments list")

    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    if not user_id:
        raise BadRequest("Missing user_id")

    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(user_id)

    service.save_appointments(date, payload["appointments"])

    return make_response(message="Appointments saved successfully"), 200

@binder_blueprint.route("/appointments/lock", methods=["POST"])
def lock_appointments():
    """
    Body:
        { "domain": "...", "user_id": "...", "date": "...", "no": <int> }
    """
    payload = request.get_json(force=True)
    no = payload.get("no")
    if no is None:
        raise BadRequest("Missing 'no' field")

    service = _get_domain_and_service(payload) 
    service.set_current_user(payload["user_id"])

    service.lock_appointment(payload["date"], int(no))

    return make_response(message="Appointment locked."), 200
