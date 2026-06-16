from flask import current_app, request, session,Blueprint
from werkzeug.exceptions import BadRequest, NotFound

from routes.binder_routes import _get_domain_and_service, DEFAULT_DOMAIN
from services.binder_service import BinderServiceError
from utils.make_res import make_response
from utils.log_events import log_event

transaction_blueprint = Blueprint("transaction_blueprint", __name__)


# Error handlers for the blueprint
@transaction_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@transaction_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@transaction_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404


@transaction_blueprint.route("/clients/<client_id>/transactions", methods=["GET"])
def list_transactions(client_id: str):
    """
    List all transactions for a specific client with pagination.

    Expects:
        client_id (str): The target client ID.
        domain (str, optional): Query param.
        user_id (str, optional): Query param.
        start_at (int, optional): The starting index for pagination (default 0).
        limit (int, optional): The number of records to return (default 10).

    Returns:
        JSON: {status: "success", data: list[Dict], message: "Transactions retrieved."}
    """
    domain = request.args.get("domain", session.get("domain", DEFAULT_DOMAIN))
    user_id = request.args.get("user_id", session.get("user_id"))
    
    start_at = int(request.args.get("start_at", 0))
    limit = int(request.args.get("limit", 10))

    service = _get_domain_and_service({"domain": domain})
    if user_id:
        service.set_current_user(user_id)

    if not user_id == session.get("user_id"):
        return make_response(status="error", message="Unauthorized action"), 401

    transactions = service.list_transactions(
        client_id=client_id, 
        start_at=start_at, 
        limit=limit
    )
    
    return make_response(data=transactions, message="Transactions retrieved."), 200

@transaction_blueprint.route("/clients/<client_id>/transactions/<int:transaction_no>", methods=["GET"])
def get_transaction(client_id: str, transaction_no: int):
    """
    Retrieve a specific transaction by its index/number.

    Expects:
        client_id (str): The target client ID.
        transaction_no (int): The specific transaction index.

    Returns:
        JSON: {status: "success", data: Dict, message: "Transaction retrieved."}
    """
    domain = request.args.get("domain", session.get("domain", DEFAULT_DOMAIN))
    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(session.get("user_id"))

    idx = transaction_no - 1 if transaction_no > 0 else 0
    
    transaction = service.read_transaction(client_id=client_id, transaction_no=idx)
    if not transaction:
        raise NotFound(f"Transaction {transaction_no} not found for client {client_id}")

    return make_response(data=transaction, message="Transaction retrieved."), 200

@transaction_blueprint.route("/clients/<client_id>/transactions", methods=["POST"])
def add_transactions(client_id: str):
    """
    Add an transaction for a client.

    Expected JSON:
    {
       "domain":"medical" | "business",
       "user_id":"...",
       "transaction": { ... }
    }
    """
    payload = request.get_json(force=True)
    if "transaction" not in payload:
        raise BadRequest("Missing 'transaction' payload")

    service = _get_domain_and_service(payload)
    if "user_id" in payload:
        service.set_current_user(payload["user_id"])

    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    if int(client_id) < 0:
        client_id = session["client_id"]

    transaction = service.create_transaction(client_id, payload["transaction"])

    transaction_no = payload["transaction"].get("vno",payload["transaction"].get("transaction_no")) 

    transaction_no = transaction_no-1 or 0

    log_event(service._binder, 202, metadata={"id" : client_id , "transaction_no":transaction_no})
    return make_response(data=transaction, message="Transaction created."), 201

@transaction_blueprint.route("/clients/<client_id>/transactions", methods=["PATCH"])
def update_transactions(client_id: str):
    """
    Update transaction for a client.

    Expected JSON:
    {
       "domain" (str): "...",
       "user_id" (str): "...",
       "transaction_no (int):"...",
       "patch" (list[Any]): { ... }
    }
    """
    payload = request.get_json(force=True)
    if "patch" not in payload:
        raise BadRequest("Missing 'patch' payload")
    
    if "transaction_no" not in payload:
        raise BadRequest("Missing 'transaction_no' payload")

    service = _get_domain_and_service(payload)
    service.set_current_user(session["user_id"])
    if "user_id" in payload:
        service.set_current_user(payload["user_id"])

    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401
    
    if  int(client_id) < 0:
        client_id = session["client_id"]

    transaction_no = int(payload["transaction_no"])- 1
    if not transaction_no > 0 :
        transaction_no = 0

    service.update_transaction(client_id=client_id,transaction_no=transaction_no,patch = payload["patch"])

    log_event(service._binder, 402, metadata={"id" : client_id , "transaction_no":transaction_no})
    return make_response(data=payload, message="Updated Transactions."), 201

@transaction_blueprint.route("/clients/<client_id>/transactions", methods=["DELETE"])
def delete_transaction(client_id: str):
    """
    Delete transaction for a client.

    Expected JSON:
    {
       "domain" (str): "...",
       "transaction_no (int):"...",
       "user_id" (str): "..."
    }
    """
    payload = request.get_json(silent=True) or {}
    service = _get_domain_and_service(payload)
    transaction_no = payload.get("transaction_no")
    user_id = payload.get("user_id")
    if user_id:
        service.set_current_user(user_id)
    
    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401
    
    if not transaction_no:
        raise BadRequest("'transaction_no' not found in payload")

    service.delete_transaction(client_id=client_id , transaction_no = transaction_no)
    return make_response(data=payload, message="Deleted Transactions."), 201
