'''
test_binder_routes.py
-----------------
test the binder routes
'''

import json
import pytest
from flask import Flask
from routes.binder_routes import binder_blueprint

class DummyBinder:
    def __init__(self):
        self.users = {}
        self.current_user = None
        self.clients = {}

    def create(self, data):
        self.users[data["id"]] = data
        self.current_user = data["id"]
        return data

    def set_current_user(self, uid):
        self.current_user = uid

    def create_client(self, client):
        self.clients[client["id"]] = client
        return client

    def read_client(self, client_id):
        return self.clients.get(client_id)

    def update_client(self, cid, patch):
        if cid not in self.clients:
            raise KeyError
        self.clients[cid].update(patch)

    def delete_client(self, cid):
        self.clients.pop(cid, None)

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(binder_blueprint)
    app.config["BINDERS"] = {"business": DummyBinder()}
    return app

def test_create_user_and_add_client(client):
    payload = {"domain":"business","user":{"id":"u1","name":"A"}}
    r = client.post("/api/binder/create_user", json=payload)
    assert r.status_code == 201
    data = r.get_json()
    assert data["status"] == "success"
    assert data["data"]["id"] == "u1"

    add_client_payload = {"domain":"business","user_id":"u1","client":{"id":"c1","name":"C"}}
    r = client.post("/api/binder/clients", json=add_client_payload)
    assert r.status_code == 201
    data = r.get_json()
    assert data["data"]["id"] == "c1"
