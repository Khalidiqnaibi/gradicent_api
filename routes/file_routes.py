"""
file_routes.py
--------------
Patient / client documents (mounted at /api/binder/files). Every route acts on the signed-in
user's own files in one workspace (domain).

  POST   /uploads              {domain, client_id, name, content_type, size} -> one-time signed upload URL
  POST   ""                    {domain, client_id, path, name, category}     -> save the uploaded file
  GET    ""?domain&client_id[&category]                                      -> list a client's files
  GET    /<file_id>/url?domain[&download=1]                                  -> short-lived signed link
  DELETE /<file_id>?domain                                                   -> remove from the record
"""

from flask import Blueprint, request, session, current_app

from routes.binder_routes import DEFAULT_DOMAIN, _get_domain_and_service
from services.file_service import FileServiceError
from utils.log_events import log_event
from utils.make_res import make_response

file_routes = Blueprint("file_routes", __name__)


def get_file_service():
    services = current_app.extensions.get("services", {})
    file_service = services.get("file_service")
    return file_service


@file_routes.errorhandler(FileServiceError)
def handle_file_error(err: FileServiceError):
    return make_response(message=str(err), status="error", code=err.code)


@file_routes.before_request
def require_user():
    if request.method != "OPTIONS" and not session.get("user_id"):
        return make_response(status="error", message="unauthenticated", code=401)
    return None


def _payload():
    return request.get_json(silent=True) or {}


def _require_own_client(domain: str, client_id) -> None:
    """Files can only be attached to / listed for a client or patient the user actually has."""
    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(session["user_id"])
    try:
        client = service.read_client(str(client_id))
    except Exception:
        client = None
    if not client:
        raise FileServiceError("Client or patient not found.", 404)


@file_routes.route("/uploads", methods=["POST"])
def create_upload():
    payload = _payload()
    domain = payload.get("domain", DEFAULT_DOMAIN)
    client_id = str(payload.get("client_id") or "")
    file_service = get_file_service()
    _require_own_client(domain, client_id)

    data = file_service.prepare_upload(
        domain=domain,
        user_id=session["user_id"],
        client_id=client_id,
        name=payload.get("name"),
        content_type=payload.get("content_type"),
        size=payload.get("size"),
    )
    return make_response(data=data, message="Upload ready", code=201)


@file_routes.route("", methods=["POST"])
def register_upload():
    payload = _payload()
    domain = payload.get("domain", DEFAULT_DOMAIN)
    client_id = str(payload.get("client_id") or "")
    file_service = get_file_service()
    _require_own_client(domain, client_id)

    data = file_service.register_upload(
        domain=domain,
        user_id=session["user_id"],
        client_id=client_id,
        path=payload.get("path"),
        name=payload.get("name"),
        category=payload.get("category"),
    )

    service = _get_domain_and_service({"domain": domain})
    service.set_current_user(session["user_id"])
    log_event(service._binder, 203, metadata={"client_id": client_id, "file_id": data.get("id")})
    return make_response(data=data, message="File saved", code=201)


@file_routes.route("", methods=["GET"])
def list_files():
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    client_id = request.args.get("client_id") or request.args.get("client_no") or ""
    files = get_file_service().list_files(
        domain=domain,
        user_id=session["user_id"],
        client_id=client_id,
        category=request.args.get("category") or None,
    )
    return make_response(data=files, message="files")


@file_routes.route("/<file_id>/url", methods=["GET"])
def file_url(file_id: str):
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    download = request.args.get("download") in ("1", "true", "yes")
    data = get_file_service().signed_url(
        domain=domain, user_id=session["user_id"], file_id=file_id, download=download,
    )
    return make_response(data=data, message="signed url")


@file_routes.route("/<file_id>", methods=["DELETE"])
def delete_file(file_id: str):
    domain = request.args.get("domain", DEFAULT_DOMAIN)
    get_file_service().delete(domain=domain, user_id=session["user_id"], file_id=file_id)
    return make_response(message="File deleted")
