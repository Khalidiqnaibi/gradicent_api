from flask import Blueprint, current_app, request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import _get_domain_and_service, DEFAULT_DOMAIN
from services.binder_service import BinderServiceError
from utils.make_res import make_response
from utils.log_events import log_event

user_blueprint = Blueprint("user_blueprint", __name__)


# Error handlers for the blueprint
@user_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error", code=400)

@user_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error", code=400)

@user_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error", code=404)


@user_blueprint.route("/user/<user_id>",methods=["GET"])
def get_user(user_id):
    '''
    get user data from binder

    Expects:
        user_id(str): target id
        domain (str) : the domain of the target (optional)
    
    Returns:
        user (Dict[str:Any]): the target users data
    '''

    payload = {
        "user_id":user_id,
        "domain" : request.args.get("domain",session.get("domain", session.get("binder", DEFAULT_DOMAIN)))
    }

    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action", code=401)
    
    service = _get_domain_and_service(payload=payload)

    user = service.get_user(payload['user_id'])
    if not user:
        raise NotFound(f"User {payload['user_id']} not found")

    return make_response(data=user,message="User retrieved successfully", code=200)

@user_blueprint.route("/user/<user_id>",methods=["PATCH"])
def update_user(user_id):
    '''
    updatess user info ussing the current binder service

    expects:
        domain (str)
        user (dict[str:Any]) # new user data

    '''
    payload = request.get_json(force=True)

    if user_id is None:
        return make_response(message="user_id cann not be null", status="error", code=400)

    if not user_id == session.get("user_id"):
        return make_response(None, message="Unauthorized action", status="error", code=401)
    
    if payload.get("domain"):
        session["domain"] = payload["domain"]
    
    payload["domain"] = session.get("domain", session.get("binder", DEFAULT_DOMAIN))

    if not payload.get("user"):
        return make_response(message="New user data can not be Null", status="error", code=400)
    
    service = _get_domain_and_service(payload=payload)

    service.update_user(payload["domain"] , payload["user_id"] , payload["user"])
    log_event(service._binder,400)
    return make_response(data=payload , message="updated successfully")

@user_blueprint.route("/user", methods=["POST"])
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
    log_event(service._binder,200)
    return make_response(data=user, message="User created successfully."), 201

@user_blueprint.route("/set_current_user", methods=["POST"])
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
    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action", code=401)

    service = _get_domain_and_service(payload)
    service.set_current_user(payload["user_id"])
    return make_response(message="Current user set.", code=200)
