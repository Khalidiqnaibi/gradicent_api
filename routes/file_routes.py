from flask import Blueprint, request, jsonify, session

from services.file_service import FileService
from binder import FirebaseFileStorageAdapter

file_routes = Blueprint("file_routes", __name__)

file_service = FileService(FirebaseFileStorageAdapter())


@file_routes.route("/upload_file", methods=["POST"])
def upload_file():
    user_id = session.get("user_id")
    file = request.files.get("file")
    client_no = request.form.get("client_no")
    folder = request.form.get("folder")

    if not all([user_id, file, client_no, folder]):
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
    client_no = request.args.get("client_no")
    folder = request.args.get("folder")

    files = file_service.list_files(
        client_no=client_no,
        user_id=user_id,
        folder=folder,
    )

    return jsonify({"status": "success", "data": files})


@file_routes.route("/delete_file", methods=["DELETE"])
def delete_file():
    file_url = request.args.get("url")
    if not file_url:
        return jsonify({"status": "error", "message": "url required"}), 400

    deleted = file_service.delete(file_url=file_url)

    if not deleted:
        return jsonify({"status": "error", "message": "Not found"}), 404

    return jsonify({"status": "success", "message": "File deleted"})
