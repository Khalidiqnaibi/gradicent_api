from flask import Blueprint, current_app, make_response, request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import DEFAULT_DOMAIN, _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.log_events import log_event
from utils.make_res import make_response

employee_blueprint = Blueprint("employee", __name__)

# Error handlers for the blueprint
@employee_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@employee_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@employee_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404


@employee_blueprint.route("/employees/<eid>", methods=["GET"])
def get_employee(eid):
    """
    Retrieve a single employee by id for the current user.

    Query param:
        domain (optional)
        user_id (optional)
    """
    if eid is None:
        return make_response(message="Employee id can not be None" , status="error") , 400
    
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    
    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401
    
    service = _get_domain_and_service({"domain": domain})

    if user_id:
        service.set_current_user(user_id)

    employee = service.read_employee(eid)

    if not employee:
        raise NotFound(f"Employee {eid} not found")
    
    return make_response(data=employee), 200 

@employee_blueprint.route("/employees", methods=["POST"]) 
def add_employee():
    '''
    Add an employee 

    Request JSON:
        {
            "domain" : "medical" || "business"
            "user_id": "...",          # optional
            "employee" :{ ... }
        }

    Response:
        { "data": "<new_employee>" , message : "" , status : "success" }
    '''
    payload = request.get_json(force=True)

    if not payload.get('domain'):
       return make_response(message="Domain cannot be empty", status="error"), 400
    
    if not payload.get("employee"):
        return make_response(message="Employee data cannot be empty", status="error"), 400
    
    service = _get_domain_and_service(payload)

    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(payload["user_id"])


    employee = service.create_employee(data=payload["employee"])
    log_event(service._binder,206)

    return make_response(data=employee, message="Created new employee", status="success"), 201

@employee_blueprint.route("/employee/<eid>", methods=["PATCH"])
def update_employee(eid):
    '''
    Update a employee for the current user.

    Expected JSON:
    {
       "domain": "...",
       "user_id": "...",
       "patch": { ... }
    }
    '''

    payload = request.get_json(force=True)
    if "patch" not in payload:
        raise BadRequest("Missing 'patch' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        if not payload['user_id'] == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(payload["user_id"])

    
    

    employee = service.update_employee(eid, payload["patch"])
    log_event(service._binder,406)
    return make_response(data=employee,message="Employee updated successfully."), 200

@employee_blueprint.route("/employee/<eid>", methods=["DELETE"])
def delete_employee(eid):
    '''
    Delete employee by id
    '''
    if eid is None:
        return make_response(message="Employee id can not be None",status="error"), 400
    
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)
    user_id = payload.get("user_id")
    if user_id:
        if not user_id == session["user_id"]:
            return make_response(status="error" , message="Unauthorized action") , 401
        service.set_current_user(user_id)


    service.delete_employee(eid)
    return make_response(message="Client deleted."), 200

@employee_blueprint.route("/employee/search", methods=["POST"])
def employee_search():
    """
    Unified search for employee endpoint.
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

    results = service.search_employee(query)
    resp = make_response(data=results, message="Search completed.")
    resp.status_code = 200
    log_event(service._binder,300)
    return resp

@employee_blueprint.route("/employee", methods=["GET"])
def list_employees():
    """
    List employees for the current user.

    Query param:
        domain (optional)
        user_id (optional)
        limit (optional)
        start_at (optional)

    Response: 
        { status, data: { employees: [...] }, message }
    """
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    user_id = request.args.get("user_id")
    start_at = request.args.get("start_at", type=int, default=0)
    limit = request.args.get("limit", type=int, default=100)

    if user_id and not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    user_id = user_id or session["user_id"]

    service = _get_domain_and_service({
        "domain": domain,
        "user_id": user_id
    })

    service.set_current_user(user_id)
    employees = service.list_employees(
        start_at=start_at,
        limit=limit
    )

    return make_response(data={"employees": employees}, message="Employee list retrieved successfully."), 200