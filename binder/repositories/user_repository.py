"""
user_repository.py
------------------
Handles user-specific data operations and extensions.
"""

from typing import Dict, Any, Optional
from binder import User, BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "users", User)

    def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user = User(**data)
        return self.create(user.to_dict())

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        results = self.list(filters={"email": email})
        return results[0] if results else None

    def update_user_metadata(self, user_id: str, key: str, value: Any) -> None:
        self.update(user_id, {"metadata": {key: value}})
