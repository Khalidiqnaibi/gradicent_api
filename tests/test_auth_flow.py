'''
test_auth_flow.py
-----------------
test the auth functionality
'''

def test_provision_user_creates_user(tmp_path, monkeypatch):
    # small example: mock user_repo and provider
    class DummyRepo:
        def __init__(self):
            self.store = {}
        def find_by_provider_id(self, p, id): return None
        def create_user(self, u): self.store[u["id"]] = u
        def save_refresh_token(self, uid, rt): self.store[uid]["metadata"]["refresh_token"] = rt
        def find_by_id(self, uid): return self.store.get(uid)
        def get_stored_refresh_token(self, uid): return self.store[uid]["metadata"]["refresh_token"]
        def clear_refresh_token(self, uid): self.store[uid]["metadata"]["refresh_token"] = None

    repo = DummyRepo()
    config = {"OAUTH_CLIENT_SECRETS_FILE": "tests/dummy.json", "OAUTH_REDIRECT_URI":"http://x","OAUTH_SCOPES":[], "SECRET_KEY":"test"}
    from auth.auth_service import AuthService
    s = AuthService(repo, config)
    # Monkeypatch provider exchange
    s.providers["google"] = type("P", (), {"exchange_code_for_user": lambda self, code: {"id": "123", "email": "a@b.c", "name":"A", "raw":{}}})()
    user, tokens = s.handle_provider_callback("google", "dummycode")
    assert user["id"].startswith("google:")
    assert "access_token" in tokens
