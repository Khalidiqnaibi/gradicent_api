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
from typing import Any, Dict, Optional
from flask import Blueprint, request, jsonify, current_app , session
from werkzeug.exceptions import BadRequest, NotFound

from services.binder_service import BinderService, BinderServiceError
from utils.get_plan_status import compute_plan_status, get_plan_data
from config import BACKEND_URL , MIN_SEC_REC
from utils.log_events import log_event , log_time_spent
from utils.make_res import make_response

binder_blueprint = Blueprint("binder", __name__)

# Constants
DEFAULT_DOMAIN = "business"

def _get_domain_and_service(payload: Dict[str, Any]) -> BinderService:
    """
    Resolve domain from payload and return a BinderService that wraps the configured binder.

    Raises:
        BadRequest: if domain is missing or binder not configured.
    """
    services = current_app.extensions.get("services", {})
    binder_services = services.get("binder_services")

    domain = payload.get("domain", DEFAULT_DOMAIN)
    binder_service = binder_services.get(domain)
    if not binder_service:
        current_app.logger.error("Binder not configured for domain: %s", domain)
        raise BadRequest(f"Unknown domain: {domain}")
    return binder_service

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

@binder_blueprint.route("/get_plan_status",methods=["GET"])
def get_plan_status():
    domain = request.args.get("domain", session.get("domain", session.get("binder", DEFAULT_DOMAIN)))
    payload ={
        "domain": domain
    }
    service = _get_domain_and_service(payload)
    user_id = session["user_id"]
    service.set_current_user(user_id)
    plan , first  = get_plan_data(service=service)
    
    status ,days = compute_plan_status(plan,first)

    result = {
        "days": days,
        "status":status,
        "plan": plan
    }
    if session.get("plan") == "sec":
        result["plan"] = session["plan"]
        return make_response(data=result) , 200
    return make_response(data=result) , 200

@binder_blueprint.route("/get_domain",methods=["GET"])
def get_domain():
    domain = session.get("domain", session.get("binder", DEFAULT_DOMAIN))
    return make_response(data=domain) , 200

@binder_blueprint.route("/track_time", methods=["POST"])
def log_time_tracking():
    """
    Log time tracking entry for the current user.

    Expected JSON:
    {
        "domain": "...",
        "user_id": "...",
        "seconds": { ... }
    }
    """
    payload = request.get_json(force=True)
    payload["domain"] = payload.get("domain",session.get("domain", session.get("binder", DEFAULT_DOMAIN)))
    if "seconds" not in payload:
        raise BadRequest("Missing 'seconds' payload")
    
    time_entry = payload["seconds"]
    if int(time_entry) < MIN_SEC_REC : 
        return make_response(data=payload, message="Time entry below minimum."), 200
    
    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(payload["user_id"])
    
    seconds_spent = payload.get("seconds", 0)
    service.set_current_user(session["user_id"])
    log_time_spent(service._binder , seconds_spent)

    return make_response(data=time_entry, message="Time entry logged."), 201

@binder_blueprint.route("/code", methods=["POST"])
def rotate_security_code():
    """
    Rotate (refresh) the current user's permission code.

    Preconditions:
    - User must be authenticated
    - User must be on the settings page
    - Provided code must match the stored code

    Request JSON:
        { 
            "user_id" (str) : id, 
            "domain" (str) : "medical" | "bessniss", # optional
            "code": "<current_code>" 
        }

    Response:
        { "data": "<new_code>" , message : "" , status : "success" }
    """
    
    payload = request.get_json(force=True)
    if  not "domain" in payload :
        payload["domain"] = session.get("domain", session.get("binder", DEFAULT_DOMAIN))

    if "user_id" not in payload  or session.get("page") != "settings":
        return make_response(status="error",message= "Unauthorized"), 401

    provided_code = request.json.get("code")
    if not provided_code:
        return make_response(status="error", message="Code required"), 400

    service = _get_domain_and_service(payload=payload)

    user = service.get_user(payload["user_id"])
    ac = user.get("settings", {}).get("ac") if user else None

    if ac and ac.get("code") != provided_code:
        return make_response(status="error", message="Invalid code"), 401

    new_code = service.rotate_permission_code(
        domain=payload["domain"],
        user_id=payload["user_id"],
        plan="sec",
    )

    return make_response(data=new_code , message="Created code success") , 201

@binder_blueprint.route("/code/check", methods=["POST"])
def check_activation_code():
    """
    Validate an activation code and activate the corresponding plan.

    Request JSON:
        { 
            "code": "<the_code>" 
        }

    Response:
        { "data": "<the_code>" , message : "accepted"  , status : "success" }

    Flow:
    - Validate via BinderService
    - Increment usage count
    - Bind session to code owner
    """
    
    payload = request.get_json(silent=True) or request.form.to_dict()
    payload["domain"] = session.get("domain", session.get("binder", DEFAULT_DOMAIN))
    
    if not payload["code"]:
        return make_response(message="code can not be null" , status="error"), 400

    service = _get_domain_and_service(payload=payload)

    res = service.validate_permission_code(
        domain=payload["domain"],
        code=payload["code"],
    )

    if not res:
        return make_response(status="error" , message="code not valid") , 401

    service.consume_permission_code(
        domain=payload["domain"],
        owner_user_id=res["owner_user_id"],
    )

    session["plan"] = res["plan"]
    session["user_id"] = res["owner_user_id"]

    return make_response(data=payload["code"], message="Code accepted, plan activated.") , 200
