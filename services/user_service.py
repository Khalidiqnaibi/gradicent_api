"""
user_service.py
---------------
Handles user lifecycle management: registration, authentication, profile updates,
and account deletion.

Follows SOLID principles:
- SRP: Manages only user domain logic.
- DIP: Depends on UserRepository abstraction (via StorageAdapter).
"""

from typing import Dict, Any, Optional
from binder import UserRepository,User


class UserService:
    """
    Service layer for user operations. Bridges routes and repositories.
    """

    def __init__(self, adapter):
        self.repo = UserRepository(adapter)

    def register_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registers a new user in the system.
        """
        if not data.get("id") or not data.get("name"):
            raise ValueError("User must have an ID and name.")
        return self.repo.create_user(data)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information by ID.
        """
        return self.repo.read(user_id)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user record by email.
        """
        return self.repo.get_user_by_email(email)

    def update_user(self, user_id: str, patch: Dict[str, Any]) -> None:
        """
        Update user attributes or metadata.
        """
        self.repo.update(user_id, patch)

    def delete_user(self, user_id: str) -> None:
        """
        Delete user record completely.
        """
        self.repo.delete(user_id)
