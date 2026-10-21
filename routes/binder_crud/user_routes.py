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

    if not payload['user_id'] == session.get("user_id"):
        return make_response(status="error" , message="Unauthorized action", code=401)
    
    service = _get_domain_and_service(payload=payload)

    user = service.get_user(payload['user_id'])
    if not user:
        raise NotFound(f"User {payload['user_id']} not found")

    return make_response(data=_public_user(user), message="User retrieved successfully", code=200)


# Profile fields a signed-in user may change about themselves. Everything else on the record
# (plan, access codes, appointments, tokens) is managed by the server and can't be patched here.
EDITABLE_PROFILE_FIELDS = {
    "name", "phone", "company", "job_title", "specialty", "license_number", "clinic", "preferences",
}


def _public_user(user):
    """Copy of the user record without server-side secrets (the stored refresh token)."""
    public = dict(user)
    metadata = public.get("metadata")
    if isinstance(metadata, dict) and "refresh_token" in metadata:
        public["metadata"] = {k: v for k, v in metadata.items() if k != "refresh_token"}
    return public


@user_blueprint.route("/user/<user_id>",methods=["PATCH"])
def update_user(user_id):
    '''
    Update the signed-in user's own profile.

    expects:
        domain (str, optional): workspace whose profile to update
        user (dict[str:Any]): fields to change (see EDITABLE_PROFILE_FIELDS)
    '''
    payload = request.get_json(force=True, silent=True) or {}

    if not user_id or user_id != session.get("user_id"):
        return make_response(None, message="Unauthorized action", status="error", code=401)

    changes = payload.get("user")
    if not isinstance(changes, dict) or not changes:
        return make_response(message="New user data can not be empty", status="error", code=400)

    patch = {k: v for k, v in changes.items() if k in EDITABLE_PROFILE_FIELDS}
    if not patch:
        return make_response(message="None of the provided fields can be changed", status="error", code=400)
    if "name" in patch and not str(patch["name"] or "").strip():
        return make_response(message="Name can not be empty", status="error", code=400)

    domain = payload.get("domain") or session.get("domain", session.get("binder", DEFAULT_DOMAIN))
    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(user_id)

    updated = service.update_user(user_id, patch)
    log_event(service._binder, 400)
    return make_response(data=_public_user(updated or {}), message="Profile updated successfully.", code=200)

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
    return make_response(data=user, message="User created successfully.", code=201)

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
    
    if not payload['user_id'] == session.get("user_id"):
        return make_response(status="error" , message="Unauthorized action", code=401)

    service = _get_domain_and_service(payload)
    service.set_current_user(payload["user_id"])
    return make_response(message="Current user set.", code=200)
