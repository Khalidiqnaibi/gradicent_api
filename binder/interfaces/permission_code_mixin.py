"""
Permission Code Mixin
=====================

Reusable mixin that adds permission / activation code behavior
to any service that exposes:

    self.adapter : UnitedFirebaseAdapter

Design:
- No state
- No direct Firebase access
- Uses user metadata storage
- Provider-agnostic user_id
"""

from datetime import datetime
import secrets
import string
from typing import Optional, Dict


class PermissionCodeMixin:
    """
    Mixin providing permission / activation code functionality.

    Intended to be mixed into domain services that already
    use UnitedFirebaseAdapter.

    Required attributes on consumer:
        - self.adapter (UnitedFirebaseAdapter)
    """

    def _random_part(self, length: int = 8) -> str:
        """
        Generate a secure random alphanumeric string.

        Args:
            length (int): Length of random suffix.

        Returns:
            str: Random string.
        """
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))

    def _generate_code(self, user_id: str) -> str:
        """
        Generate a permission code bound to a user.

        Format:
            <user_id>:<random_suffix>

        Args:
            user_id (str): Code owner.

        Returns:
            str: Permission code.
        """
        return f"{user_id}:{self._random_part()}"

    def rotate_permission_code(
        self,
        domain: str,
        user_id: str,
        plan: str = "sec",
    ) -> str:
        """
        Create or rotate a permission code for a user.

        This replaces any existing code and resets counters.

        Args:
            domain (str): Domain name (e.g. 'drs').
            user_id (str): User identifier.
            plan (str): Subscription / permission plan.

        Returns:
            str: Newly generated permission code.
        """
        user = self.adapter.get_user(domain, user_id) or {}
        settings = user["metadata"].get("settings", {})

        code = self._generate_code(user_id)

        settings["ac"] = {
            "code": code,
            "plan": plan,
            "users": 0,
            "active": True,
            "created_at": datetime.now().isoformat(),
        }

        user["metadata"]["settings"] = settings
        self.adapter.update_user(domain, user_id, user)

        return code

    def validate_permission_code(
        self,
        domain: str,
        code: str,
    ) -> Optional[Dict]:
        """
        Validate a permission code.

        Args:
            domain (str): Domain name.
            code (str): Permission code.

        Returns:
            dict | None:
                On success:
                    {
                        "owner_user_id": str,
                        "plan": str
                    }
                On failure:
                    None
        """
        if ":" not in code:
            return None

        owner_user_id, _ = code.split(":", 1)

        user = self.adapter.get_user(domain, owner_user_id)
        if not user:
            return None

        ac = user["metadata"].get("settings", {}).get("ac")
        if not ac:
            return None

        if not ac.get("active"):
            return None

        if ac.get("code") != code:
            return None

        return {
            "owner_user_id": owner_user_id,
            "plan": ac.get("plan"),
        }

    def consume_permission_code(
        self,
        domain: str,
        owner_user_id: str,
    ) -> None:
        """
        Increment usage counter for a permission code.

        Args:
            domain (str): Domain name.
            owner_user_id (str): Code owner.
        """
        user = self.adapter.get_user(domain, owner_user_id)
        if not user:
            return

        ac = user["metadata"].get("settings", {}).get("ac")
        if not ac:
            return

        ac["users"] = ac.get("users", 0) + 1
        user["metadata"]["settings"]["ac"] = ac

        self.adapter.update_user(domain, owner_user_id, user)
