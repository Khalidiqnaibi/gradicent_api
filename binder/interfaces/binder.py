"""
Binder
---------------
Provides the BaseBinder class that composes the small service interfaces
and defines shared CRUD helpers for Firebase or similar adapters.
"""

from typing import Any, Dict, Optional , List 
from abc import ABC


class Binder(ABC):
    """Base class that other binders extend to interact with adapters and Gaia."""

    def __init__(self,domain:str, adapter: Any):
        if not adapter:
            raise ValueError("Adapter cannot be None")

        self._adapter = adapter
        self._domain = domain
        self._current_user: Optional[str] = None

    # --- Dependency Access ---
    @property
    def adapter(self) -> Any:
        return self._adapter
    
    @property
    def domain(self) -> Any:
        return self._domain

    @property
    def gaia_engine(self) -> Optional[Any]:
        return self._gaia_engine

    # --- Context Control ---
    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @current_user.setter
    def current_user(self, user_id: str) -> None:
        user = self._adapter.get_user(self._domain, user_id)
        if not user:
            raise Exception(f"User {user_id} does not exist")
        self._current_user = user_id

    def _require_user(self) -> None:
        if not self._current_user:
            raise RuntimeError("Operation requires a logged-in user context")
    