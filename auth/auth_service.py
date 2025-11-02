"""
auth_service.py
----------------
AuthService: thin wrapper around OAuth flow + session handling.
The old code used Flow.from_client_secrets_file(...) — move that into here.
(Reference: app.py uses Flow.from_client_secrets_file(...)). :contentReference[oaicite:0]{index=0}
"""

from google_auth_oauthlib.flow import Flow
from flask import url_for, session, current_app, redirect, request
from typing import Optional

class AuthService:
    def __init__(self, client_secrets_path: str, redirect_uri: str):
        self.flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=["https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/userinfo.email", "openid"],
            redirect_uri=redirect_uri
        )

    def authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        return self.flow.authorization_url(include_granted_scopes='true', state=state)

    def fetch_token_and_user(self, authorization_response: str) -> dict:
        self.flow.fetch_token(authorization_response=authorization_response)
        token = self.flow.credentials._id_token
        # verify id_token as in old code (id_token.verify_oauth2_token)
        # return parsed user info dict
        # (implementation detail referencing the original verify flow) :contentReference[oaicite:1]{index=1}
