from flask import Blueprint, current_app, make_response, request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import DEFAULT_DOMAIN, _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.make_res import make_response

appointment_blueprint = Blueprint("appointment", __name__)


# Error handlers for the blueprint
@appointment_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@appointment_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@appointment_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404



@appointment_blueprint.route("/appointments/<date>", methods=["GET"])
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
    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    service = _get_domain_and_service(payload)
    service.set_current_user(payload["user_id"])

    result = service.get_appointments(date)
    return make_response(data={"appointments": result}), 200

@appointment_blueprint.route("/appointments/<date>", methods=["PATCH"])
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

    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(user_id)

    service.save_appointments(date, payload["appointments"])

    return make_response(message="Appointments saved successfully"), 200

@appointment_blueprint.route("/appointments/lock", methods=["POST"])
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
    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401
    service.set_current_user(payload["user_id"])

    service.lock_appointment(payload["date"], int(no))

    return make_response(message="Appointment locked."), 200
