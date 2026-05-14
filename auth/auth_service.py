"""
auth_service.py
----------------
Adapter-only authentication service built to work with the User dataclass.

- Google OAuth flow
- User provisioning using the User model
- JWT access + refresh token lifecycle
- Metadata refresh_token storage
- No repository, no Binder
"""

import time
import jwt
from typing import Dict, Any, Optional, Tuple
from dataclasses import asdict

from auth.providers.google_provider import GoogleAuthProvider
from binder import User 
from utils.provision_user import _provision_user

class AuthService:
    """
    Authentication service that uses only the adapter for storage.
    Ensures users are always saved using the User dataclass structure.
    """

    def __init__(
        self,
        adapter,
        google_client,
        jwt_secret: str,
        redirect_uri: str,
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 60 * 60 * 24 * 30,
    ):
        self.adapter = adapter
        self.google_client = google_client
        self.jwt_secret = jwt_secret
        self.redirect_uri = redirect_uri
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl

    def get_authorization_redirect(self, redirect_uri: str):
        """Returns a Flask Response object that handles state/session automatically."""
        return self.google_client.authorize_redirect(redirect_uri)


    def handle_provider_callback(self, domain: str, provider: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Automatically verifies state against session and exchanges code for tokens."""
        # This pulls the 'code' and 'state' from the current request context automatically
        token = self.google_client.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            raise ValueError("Failed to retrieve user info from Google.")

        provider_user = {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
        
        user = _provision_user(self.adapter, domain, provider, provider_user)
        tokens = self._create_tokens_for_user(user.id)
        self._save_refresh_token(domain, user.id, tokens["refresh_token"])

        return user.to_dict(), tokens

    def _create_tokens_for_user(self, user_id: str) -> Dict[str, Any]:
        now = int(time.time())

        access_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.access_token_ttl,
        }

        refresh_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.refresh_token_ttl,
            "type": "refresh",
        }

        return {
            "access_token": jwt.encode(access_payload, self.jwt_secret, algorithm="HS256"),
            "refresh_token": jwt.encode(refresh_payload, self.jwt_secret, algorithm="HS256"),
            "expires_in": self.access_token_ttl,
        }

    def verify_token_and_get_user(self,domain:str, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            raw_user = self.adapter.get_user(domain,payload["sub"])
            return raw_user if raw_user else None
        except Exception:
            return None


    def sign_out(self,domain:str, user_id: str) -> None:
        self._save_refresh_token(domain,user_id, None)

    def _save_refresh_token(self,domain:str, user_id: str, token: Optional[str]):
        raw = self.adapter.get_user(domain,user_id)
        if not raw:
            return

        # LEGACY SAFE
        if "metadata" not in raw or "first" in raw:
            raw["metadata"] = {}

        raw["metadata"]["refresh_token"] = token

        # Save back without enforcing dataclass structure
        self.adapter.update_user(domain,user_id, raw)

    def _get_stored_refresh_token(self,domain:str, user_id: str) -> Optional[str]:
        raw = self.adapter.get_user(domain,user_id)
        if not raw:
            return None

        # NEW FORMAT
        if "metadata" in raw and "first" not in raw:
            return raw.get("metadata", {}).get("refresh_token")

        # LEGACY FORMAT
        if "settings" in raw:
            return raw.get("settings", {}).get("refresh_token")

        return None