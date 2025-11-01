"""
binder_routes.py
----------------
Endpoints for Binder CRUD operations across domains.
Implements controller + service separation and unified responses.
"""

from flask import Blueprint, request, jsonify, session, current_app

binder_blueprint = Blueprint("binder", __name__)

def make_response(data=None, message="", status="success"):
    return jsonify({"status": status, "data": data, "message": message})


@binder_blueprint.route("/create_user", methods=["POST"])
def create_user():
    """
    Create a user in the selected Binder domain.
    """
    payload = request.json
    domain = payload.get("domain", "business")  # default
    binder = current_app.config["BINDERS"][domain]

    user = binder.create(payload["user"])
    binder.set_current_user(user["id"])
    return make_response(user, "User created successfully.")


@binder_blueprint.route("/add_client", methods=["POST"])
def add_client():
    """
    Add a client (or patient) under the current user.
    """
    payload = request.json
    domain = payload.get("domain", "business")
    binder = current_app.config["BINDERS"][domain]

    binder.set_current_user(payload["user_id"])
    client = binder.create_client(payload["client"])
    return make_response(client, "Client added successfully.")


@binder_blueprint.route("/update_client", methods=["PATCH"])
def update_client():
    payload = request.json
    domain = payload.get("domain", "business")
    binder = current_app.config["BINDERS"][domain]

    binder.set_current_user(payload["user_id"])
    binder.update_client(payload["client_id"], payload["patch"])
    return make_response(message="Client updated successfully.")
