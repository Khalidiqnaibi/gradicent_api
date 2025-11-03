"""
auth_provider.py
----------------
AuthProvider interface: requirement for any external auth provider.
"""
from typing import Dict

class AuthProvider:
    """
    Interface for OAuth/OpenID providers.
    """

    def get_authorization_url(self, state: str = None) -> str:
        """Return a full URL to redirect the user to."""
        raise NotImplementedError

    def exchange_code_for_user(self, code: str) -> Dict:
        """
        Exchange authorization code for tokens/user info.
        Returns dict with at least: { 'id': str, 'email': str, 'name': str, 'raw': {...} }
        """
        raise NotImplementedError
