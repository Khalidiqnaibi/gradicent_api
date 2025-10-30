"""
Binder
---------------
Provides the BaseBinder class that composes the small service interfaces
and defines shared CRUD helpers for Firebase or similar adapters.
"""

from typing import Any, Dict, Optional
from .binder_interface import (
    IUserService, IClientService, IEmployeeService,
    IProductService, IServiceService, IInteractionService, ITransactionService
)


class Binder(
    IUserService,
    IClientService,
    IEmployeeService,
    IProductService,
    IServiceService,
    IInteractionService,
    ITransactionService
):
    """
    Binder implements common logic and CRUD helpers used across domains.
    """

    def __init__(self, adapter: Any, gaia_engine: Optional[Any] = None):
        if adapter is None:
            raise ValueError("adapter cannot be None")
        self._adapter = adapter
        self._gaia_engine = gaia_engine
        self._current_user: Optional[str] = None

    # -------- Properties --------
    @property
    def adapter(self) -> Any:
        return self._adapter

    @adapter.setter
    def adapter(self, value: Any) -> None:
        if value is None:
            raise ValueError("adapter cannot be None")
        self._adapter = value

    @property
    def gaia_engine(self) -> Optional[Any]:
        return self._gaia_engine

    @gaia_engine.setter
    def gaia_engine(self, engine: Any) -> None:
        self._gaia_engine = engine

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @current_user.setter
    def current_user(self, user_id: str) -> None:
        self._current_user = user_id

    def _require_user(self) -> None:
        if not self._current_user:
            raise RuntimeError("Current user is not set")

    # -------- Common CRUD Helpers --------
    def _create(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.push(path, data)
        return data

    def _read(self, path: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get(path)

    def _update(self, path: str, patch: Dict[str, Any]) -> None:
        self.adapter.update(path, patch)

    def _delete(self, path: str) -> None:
        self.adapter.delete(path)
