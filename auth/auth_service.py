"""
auth_service.py
----------------
AuthService: orchestrates external providers, user provisioning and token lifecycle.

This implementation intentionally uses the existing UserRepository methods you already have:
- create_user(data: Dict[str, Any])
- get_user_by_email(email: str) -> Optional[Dict[str, Any]]
- update_user_metadata(user_id: str, key: str, value: Any) -> None

It also attempts to use `get(user_id)` on the repository (typical BaseRepository API) to
fetch a user by id when needed.
"""
from typing import Dict, Any, Tuple, Optional
import time
import jwt

from binder import UserRepository  
from auth.providers.google_provider import GoogleAuthProvider


class AuthService:
    """
    High-level auth operations. Designed for dependency injection: pass a UserRepository instance
    and an app config dict to the constructor.
    """

    def __init__(self, user_repository: UserRepository, config: dict):
        self.user_repository = user_repository
        self.config = config or {}
        # register providers (only google by default)
        self.providers = {
            "google": GoogleAuthProvider(
                client_secrets_path=self.config["OAUTH_CLIENT_SECRETS_FILE"],
                redirect_uri=self.config["OAUTH_REDIRECT_URI"],
                scopes=self.config["OAUTH_SCOPES"],
            )
        }
        self.jwt_secret = self.config.get("SECRET_KEY", "dev-secret")
        self.access_token_ttl = int(self.config.get("ACCESS_TOKEN_TTL_SECONDS", 3600))
        self.refresh_token_ttl = int(self.config.get("REFRESH_TOKEN_TTL_SECONDS", 60 * 60 * 24 * 30))

    def get_authorization_url(self, provider_name: str, state: str = None) -> str:
        provider = self.providers[provider_name]
        return provider.get_authorization_url(state)

    def handle_provider_callback(self, provider_name: str, code: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Exchange authorization code -> provider user -> provision local user -> return (user, tokens).
        Returns:
            (user_dict, tokens_dict)
        """
        provider = self.providers[provider_name]
        provider_user = provider.exchange_code_for_user(code)
        user = self._provision_user(provider_name, provider_user)
        tokens = self._create_tokens_for_user(user["id"])
        # persist refresh token in user metadata via the repository API you already have
        self._save_refresh_token(user["id"], tokens["refresh_token"])
        return user, tokens

    def _provision_user(self, provider_name: str, provider_user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or find a local User record.
        Logic:
          1. Try to fetch by provider id (user id key = "{provider}:{provider_id}") using repo.get()
          2. Fall back to email lookup via get_user_by_email(email)
          3. Create a new user record (create_user) with id "{provider}:{provider_id}"
        Returns a user dict (storage shape).
        """
        provider_id = str(provider_user.get("id", ""))
        provider_uid = f"{provider_name}:{provider_id}"

        # 1) Try lookup by provider id (if BaseRepository provides get())
        user = None
        try:
            # BaseRepository commonly exposes a `get(id)` method
            user = self.user_repository.get(provider_uid)
        except Exception:
            user = None

        if user:
            # ensure metadata stores provider info
            try:
                self.user_repository.update_user_metadata(user["id"], "provider", provider_name)
                self.user_repository.update_user_metadata(user["id"], "provider_id", provider_id)
            except Exception:
                # ignore metadata update failures (not fatal here)
                pass
            return user

        # 2) Try lookup by email
        email = provider_user.get("email")
        if email:
            existing = self.user_repository.get_user_by_email(email)
            if existing:
                # link provider info into user's metadata
                self.user_repository.update_user_metadata(existing["id"], "provider", provider_name)
                self.user_repository.update_user_metadata(existing["id"], "provider_id", provider_id)
                return existing

        # 3) Create new user
        new_user = {
            "id": provider_uid,
            "name": provider_user.get("name") or provider_user.get("email") or provider_uid,
            "email": provider_user.get("email"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "metadata": {"provider": provider_name, "provider_id": provider_id, "raw": provider_user.get("raw", {})},
        }
        # uses your existing create_user (which wraps dataclass and storage.create)
        self.user_repository.create_user(new_user)
        return new_user

    def _create_tokens_for_user(self, user_id: str) -> Dict[str, Any]:
        now = int(time.time())
        access_payload = {"sub": user_id, "iat": now, "exp": now + self.access_token_ttl}
        refresh_payload = {"sub": user_id, "iat": now, "exp": now + self.refresh_token_ttl, "type": "refresh"}
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm="HS256")
        return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": self.access_token_ttl}

    def verify_token_and_get_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Return user dict if token valid, else None."""
        if not token:
            return None
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload["sub"]
            # try reading by id (BaseRepository.get)
            try:
                return self.user_repository.get(user_id)
            except Exception:
                # fallback: try get_user_by_email if user_id looks like an email (rare)
                if "@" in user_id:
                    return self.user_repository.get_user_by_email(user_id)
                return None
        except Exception:
            return None

    def refresh_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate refresh token and issue a new access token (stateful check against stored token).
        Returns a new token pair dict or None on failure.
        """
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != "refresh":
                raise ValueError("not a refresh token")
            user_id = payload["sub"]

            # verify stored refresh token matches (stateful rotation)
            stored = self._get_stored_refresh_token(user_id)
            if stored is None or stored != refresh_token:
                raise ValueError("refresh token mismatch")

            new_tokens = self._create_tokens_for_user(user_id)
            # persist the new refresh token
            self._save_refresh_token(user_id, new_tokens["refresh_token"])
            return new_tokens
        except Exception:
            return None

    def sign_out(self, user_id: str) -> None:
        """Revoke refresh tokens / sign-out cleanup."""
        if user_id:
            self._save_refresh_token(user_id, None)

    # ---- small helpers using your existing repository API ----
    def _save_refresh_token(self, user_id: str, refresh_token: Optional[str]) -> None:
        """Persist refresh_token into user's metadata using update_user_metadata."""
        try:
            self.user_repository.update_user_metadata(user_id, "refresh_token", refresh_token)
        except Exception:
            # don't raise (non-fatal); if your repository doesn't implement update_user_metadata
            # this will be a no-op at runtime and should be handled in logs.
            pass

    def _get_stored_refresh_token(self, user_id: str) -> Optional[str]:
        """
        Retrieve stored refresh token by reading the user record and returning metadata.refresh_token
        Attempts to use `get(user_id)` on the repository.
        """
        try:
            user = self.user_repository.get(user_id)
            if not user:
                return None
            meta = user.get("metadata") or {}
            return meta.get("refresh_token")
        except Exception:
            return None