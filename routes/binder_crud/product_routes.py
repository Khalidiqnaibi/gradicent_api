
from flask import Blueprint, current_app,request, session
from werkzeug.exceptions import BadRequest, NotFound

from routes.auth_routes import _get_domain_and_service
from services.binder_service import BinderServiceError
from utils.log_events import log_event
from utils.make_res import make_response


product_blueprint = Blueprint("product", __name__)


# Error handlers for the blueprint
@product_blueprint.errorhandler(BinderServiceError)
def handle_service_error(err: BinderServiceError):
    current_app.logger.exception("Binder service error: %s", err)
    return make_response(message=str(err), status="error"), 400

@product_blueprint.errorhandler(BadRequest)
def handle_bad_request(err: BadRequest):
    current_app.logger.warning("Bad request: %s", err)
    return make_response(message=str(err), status="error"), 400

@product_blueprint.errorhandler(NotFound)
def handle_not_found(err: NotFound):
    return make_response(message=str(err), status="error"), 404


@product_blueprint.route("/products", methods=["POST"])
def create_product():
    """
    Create a product.

    Input JSON:
        {
            "domain": str,
            "user_id": str,
            "product": dict
        }

    Returns:
        JSON envelope containing created product.
    """
    payload = request.get_json(force=True)
    if "product" not in payload:
        raise BadRequest("Missing 'product' payload")

    service = _get_domain_and_service(payload)
    if payload.get("user_id"):
        service.set_current_user(payload["user_id"])

    
    if not payload['user_id'] == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    product = service.create_product(payload["product"])
    log_event(service._binder, 204)

    return make_response(data=product, message="Product created successfully."), 201

@product_blueprint.route("/products/<product_id>", methods=["GET"])
def read_product(product_id: str):
    """
    Read a single product.

    Query Params:
        domain (str)
        user_id (str)

    Returns:
        JSON envelope containing product data.
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

    product = service.read_product(product_id)
    if not product:
        raise NotFound(f"Product {product_id} not found")

    return make_response(data=product), 200

@product_blueprint.route("/products/<product_id>", methods=["PATCH"])
def update_product(product_id: str):
    """
    Update a product.

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

    service.update_product(product_id, payload["patch"])
    log_event(service._binder, 404)

    return make_response(message="Product updated successfully."), 200

@product_blueprint.route("/products/<product_id>", methods=["DELETE"])
def delete_product(product_id: str):
    """
    Delete a product.

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

    service.delete_product(product_id)

    return make_response(message="Product deleted successfully."), 200

@product_blueprint.route("/products/search", methods=["POST"])
def product_search():
    """
    Unified search for product endpoint.
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

    results = service.search_product(query)
    resp = make_response(data=results, message="Search completed.")
    resp.status_code = 200
    log_event(service._binder, 300)
    return resp
    
@product_blueprint.route("/products", methods=["GET"])
def list_products():
    """
    List products for current user.

    Query Params:
        domain (str)
        user_id (str)
        start_at (int)
        limit (int)
    
    returns:
        {data: {products: [...]}, message, status}
    """

    domain = request.args.get("domain", session.get("domain", session.get("binder", "default")))
    user_id = request.args.get("user_id", session.get("user_id"))
    start_at = int(request.args.get("start_at", 0))
    limit = int(request.args.get("limit", 30))

    payload = {
        "domain": domain,
        "user_id": user_id
    }
    service = _get_domain_and_service(payload)

    if not user_id == session["user_id"]:
        return make_response(status="error" , message="Unauthorized action") , 401

    service.set_current_user(user_id)

    products = service.list_products(limit=limit, start_at=start_at)
    return make_response(data={"products": products}, message="Products retrieved successfully."), 200