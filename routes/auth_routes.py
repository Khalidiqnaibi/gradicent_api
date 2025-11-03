"""
auth_routes.py
--------------
Auth routes for OAuth flows and token endpoints.

Endpoints:
  GET  /start?provider=google     -> redirect to provider auth URL
  GET  /callback?provider=google  -> OAuth callback
  POST /signout                   -> sign out (session + revoke refresh token)
  GET  /me                        -> current user (session or Bearer token)
  POST /refresh                   -> exchange refresh token for new access token
"""

from typing import Optional
from flask import Blueprint, request, redirect, session, jsonify, current_app, url_for
from werkzeug.exceptions import BadRequest

auth_blueprint = Blueprint("auth", __name__)


def _get_auth_service():
    services = current_app.extensions.get("services", {})
    auth_service = services.get("auth_service")
    if not auth_service:
        raise RuntimeError("auth_service not registered in app.extensions['services']")
    return auth_service


@auth_blueprint.route("/start", methods=["GET"])
def start_oauth():
    """
    Start an OAuth/OpenID authorization flow for a provider.
    Query params:
      - provider (default: "google")
      - state (optional)
    Returns a redirect to the provider authorization URL.
    """
    provider = request.args.get("provider", "google")
    state = request.args.get("state")
    auth_service = _get_auth_service()
    try:
        auth_url = auth_service.get_authorization_url(provider, state)
    except KeyError:
        return jsonify({"status": "error", "message": f"unknown provider '{provider}'"}), 400
    return redirect(auth_url)


@auth_blueprint.route("/callback", methods=["GET"])
def oauth_callback():
    """
    OAuth callback endpoint. Provider will redirect here with `code` (and optionally `state`).
    On success:
      - create/provision user locally
      - issue JWT tokens
      - set a session cookie for browser flows
      - return user and token info as JSON
    """
    provider = request.args.get("provider", "google")
    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        return jsonify({"status": "error", "message": error}), 400
    if not code:
        raise BadRequest("missing 'code' in callback request")

    auth_service = _get_auth_service()
    try:
        user, tokens = auth_service.handle_provider_callback(provider, code)
    except Exception as exc:
        # return a safe error message
        return jsonify({"status": "error", "message": str(exc)}), 500

    # Browser flow: store session and minimal jwt
    session.permanent = True
    session["user_id"] = user.get("id")
    session["jwt"] = tokens.get("access_token")

    return jsonify({"status": "success", "data": {"user": user, "tokens": tokens}})


@auth_blueprint.route("/signout", methods=["POST"])
def sign_out():
    """
    Sign out the current session / revoke refresh token.
    Accepts optional JSON body: { "user_id": "..." } to sign out specific user.
    """
    auth_service = _get_auth_service()
    user_id = request.json.get("user_id") if request.is_json else session.get("user_id")
    # revoke server-side refresh token
    try:
        auth_service.sign_out(user_id)
    except Exception:
        # non-fatal: continue to clear session
        pass
    session.clear()
    return jsonify({"status": "success", "message": "signed out"})


@auth_blueprint.route("/me", methods=["GET"])
def current_user():
    """
    Return the current authenticated user.
    Tries Bearer token first, then session cookie.
    """
    auth_service = _get_auth_service()
    auth_header: Optional[str] = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    token = token or session.get("jwt")

    user = auth_service.verify_token_and_get_user(token)
    if not user:
        return jsonify({"status": "error", "message": "unauthenticated"}), 401
    return jsonify({"status": "success", "data": user})


@auth_blueprint.route("/refresh", methods=["POST"])
def refresh_tokens():
    """
    Exchange a refresh token for a new access token pair.
    Body: { "refresh_token": "..." }
    Returns new tokens or 401 on failure.
    """
    auth_service = _get_auth_service()
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token") or request.headers.get("X-Refresh-Token")
    if not refresh_token:
        return jsonify({"status": "error", "message": "missing refresh_token"}), 400

    new_tokens = auth_service.refresh_tokens(refresh_token)
    if not new_tokens:
        return jsonify({"status": "error", "message": "invalid or expired refresh token"}), 401

    return jsonify({"status": "success", "data": new_tokens})
