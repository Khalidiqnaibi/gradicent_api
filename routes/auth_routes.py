"""
auth_routes.py
--------------
Auth routes for OAuth flows and token endpoints.

Endpoints:
  GET  /start?provider=google    -> redirect to provider auth URL
  GET  /callback?provider=google  -> OAuth callback
  POST /signout                   -> sign out (session + revoke refresh token)
  GET  /me                        -> current user (session or Bearer token)
  POST /refresh                   -> exchange refresh token for new access token
"""

from typing import Optional, Any, Dict
from flask import Blueprint, request, redirect, session, jsonify, current_app, url_for
from werkzeug.exceptions import BadRequest, NotFound

from binder import normalize_user
from utils.log_events import log_with_service
from services.binder_service import BinderService

auth_blueprint = Blueprint("auth", __name__)

DEFAULT_DOMAIN = "business"

def _get_domain_and_service(payload: Dict[str, Any]) -> BinderService:
    """Resolve domain and return a BinderService instance."""
    services = current_app.extensions.get("services", {})
    binder_services = services.get("binder_services")

    domain = payload.get("domain", DEFAULT_DOMAIN)
    binder_service = binder_services.get(domain)
    if not binder_service:
        current_app.logger.error("Binder not configured for domain: %s", domain)
        raise BadRequest(f"Unknown domain: {domain}")
    return binder_service

def _get_auth_service(domain: str):
    """Retrieve the Authservice registered for the specific domain."""
    services = current_app.extensions.get("services", {})
    auth_services = services.get("auth_services")
    if not auth_services:
        raise RuntimeError("auth_services not registered in app.extensions")
    
    auth_service = auth_services.get(domain)
    if not auth_service:
         raise RuntimeError(f"auth_service not registered for domain: {domain}")
    return auth_service


@auth_blueprint.route("/start", methods=["GET"])
def start_oauth():
    """Start OAuth flow by redirecting to provider with managed state."""
    provider = request.args.get("provider", "google")
    domain = request.args.get("domain", session.get("binder", "business"))
    
    session["domain"] = domain
    auth_service = _get_auth_service(domain)

    # Authlib needs the full callback URL to generate the state correctly
    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    
    try:
        return auth_service.get_authorization_redirect(redirect_uri)
    except Exception as exc:
        return jsonify({"status": "error", "data": None, "message": str(exc)}), 400


@auth_blueprint.route("/callback", methods=["GET"])
def oauth_callback():
    """Handle provider callback and provision user."""
    provider = request.args.get("provider", "google")
    error = request.args.get("error")
    
    if error:
        return jsonify({"status": "error", "data": None, "message": error}), 400

    domain = session.get("domain", DEFAULT_DOMAIN)
    auth_service = _get_auth_service(domain)
    
    try:
        # State and code are handled internally via request context
        user, tokens = auth_service.handle_provider_callback(domain, provider)
    except Exception as exc:
        return jsonify({"status": "error", "data": None, "message": str(exc)}), 500

    # Store authentication in session
    session.permanent = True
    session["user_id"] = user.get("id")
    session["jwt"] = tokens.get("access_token")

    # Log login event
    binder_service = _get_domain_and_service({"domain": domain})
    binder_service.set_current_user(session.get("user_id"))
    log_with_service(binder_service, 100)

    if domain:
        return redirect(f"/binder/{domain}")

    return jsonify({"status": "success", "data": {"user": user, "tokens": tokens}, "message": "Authenticated"})


@auth_blueprint.route("/signout", methods=["POST"])
def sign_out():
    """Revoke tokens and clear local session."""
    domain = request.json.get("domain", session.get("domain", DEFAULT_DOMAIN)) if request.is_json else session.get("domain", DEFAULT_DOMAIN)
    auth_service = _get_auth_service(domain)
    user_id = request.json.get("user_id") if request.is_json else session.get("user_id")

    try:
        auth_service.sign_out(domain, user_id)
    except Exception:
        pass
    
    session.clear()
    session["domain"] = domain
    return jsonify({"status": "success", "data": None, "message": "signed out"})


@auth_blueprint.route("/me", methods=["GET"])
def current_user():
    """Return the currently authenticated user structure."""
    domain = request.args.get("domain", session.get("domain", DEFAULT_DOMAIN))
    auth_service = _get_auth_service(domain)
    
    # Check Bearer token or session JWT
    auth_header: Optional[str] = request.headers.get("Authorization")
    token = auth_header.split(" ", 1)[1].strip() if auth_header and auth_header.lower().startswith("bearer ") else session.get("jwt")
    
    user = auth_service.verify_token_and_get_user(domain, token)
    if not user:
        return jsonify({"status": "error", "data": None, "message": "unauthenticated"}), 401
    
    normalized = normalize_user(user)
    if not normalized:
        return jsonify({"status": "error", "data": None, "message": "unrecognized user structure"}), 401

    res = normalized.to_dict()
    res.pop("metadata", None) 
    return jsonify({"status": "success", "data": res, "message": "got user"})


@auth_blueprint.route("/refresh", methods=["POST"])
def refresh_tokens():
    """Exchange refresh token for new access/refresh pair."""
    payload = request.get_json(silent=True) or {}
    domain = payload.get("domain", session.get("domain", DEFAULT_DOMAIN))
    auth_service = _get_auth_service(domain)
    
    refresh_token = payload.get("refresh_token") or request.headers.get("X-Refresh-Token")
    if not refresh_token:
        return jsonify({"status": "error", "message": "missing refresh_token"}), 400

    new_tokens = auth_service.refresh_tokens(domain, refresh_token)
    if not new_tokens:
        return jsonify({"status": "error", "data": None, "message": "invalid or expired refresh token"}), 401

    return jsonify({"status": "success", "data": new_tokens, "message": "refreshed"})