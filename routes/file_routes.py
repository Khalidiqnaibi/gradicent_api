from flask import Blueprint, request, jsonify, session , current_app
from werkzeug.utils import secure_filename

file_routes = Blueprint("file_routes", __name__)

def get_file_service():
    services = current_app.extensions.get("services", {})
    file_service = services.get("file_service")
    return file_service

def _unauthorized():
    return jsonify({"status": "error", "data": None, "message": "unauthenticated"}), 401


@file_routes.route("/upload_file", methods=["POST"])
def upload_file():
    user_id = session.get("user_id")
    if not user_id:
        return _unauthorized()
    file = request.files.get("file")
    client_no = request.form.get("client_no")
    folder = request.form.get("folder")

    file_service = get_file_service()

    if not all([file, client_no, folder]) or not secure_filename(file.filename or ""):
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    data = file_service.upload(
        file=file,
        client_no=client_no,
        folder=folder,
        user_id=user_id,
    )

    return jsonify({"status": "success", "data": data})


@file_routes.route("/get_files", methods=["GET"])
def get_files():
    user_id = session.get("user_id")
    if not user_id:
        return _unauthorized()
    client_no = request.args.get("client_no")
    folder = request.args.get("folder")
    if not client_no:
        return jsonify({"status": "error", "data": None, "message": "client_no required"}), 400
    file_service = get_file_service()

    files = file_service.list_files(
        client_no=client_no,
        user_id=user_id,
        folder=folder,
    )

    return jsonify({"status": "success", "data": files})


@file_routes.route("/delete_file", methods=["DELETE"])
def delete_file():
    user_id = session.get("user_id")
    if not user_id:
        return _unauthorized()
    file_url = request.args.get("url")
    if not file_url:
        return jsonify({"status": "error", "message": "url required"}), 400

    file_service = get_file_service()
    # Scoped to the signed-in owner so nobody can delete someone else's file by URL
    deleted = file_service.delete(file_url=file_url, user_id=user_id)

    if not deleted:
        return jsonify({"status": "error", "message": "Not found"}), 404

    return jsonify({"status": "success", "message": "File deleted"})
