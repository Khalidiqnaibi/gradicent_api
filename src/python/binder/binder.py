"""
Binder
----------------
Provides the abstract BaseBinder class that combines the Binder interfaces.
Implements dependency injection for adapters and user context.
"""

from abc import ABC
from typing import Any, Optional
from binder_interface import IUserService, IClientService, IInteractionService


class Binder(IUserService, IClientService, IInteractionService, ABC):
    """
    Base class that combines all Binder services.

    Follows:
      - Single Responsibility: each subclass handles one domain.
      - Dependency Inversion: depends on adapter interface, not concrete DB.
    """

    def __init__(self, adapter: Any):
        if not adapter:
            raise ValueError("Adapter cannot be None")

        self._adapter = adapter
        self._current_user: Optional[str] = None

    # --- Properties (Encapsulation) ---
    @property
    def adapter(self) -> Any:
        """Data adapter for persistence (Firebase, SQL, etc.)."""
        return self._adapter

    @adapter.setter
    def adapter(self, adapter: Any) -> None:
        if not adapter:
            raise ValueError("Adapter cannot be None")
        self._adapter = adapter

    @property
    def current_user(self) -> Optional[str]:
        """Currently active user (google_id or user_id)."""
        return self._current_user

    @current_user.setter
    def current_user(self, user_id: str) -> None:
        self._current_user = user_id

    def _require_user(self) -> None:
        """Guard clause: ensures operations happen within a user context."""
        if not self._current_user:
            raise RuntimeError("No current user set in binder context")
