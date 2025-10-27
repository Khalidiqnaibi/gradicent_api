"""
Binder Interface
---
Defines abstract interfaces for the Binder system.
Implements SOLID principles by separating concerns clearly.

Each interface focuses on *one* responsibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IUserService(ABC):
    """Defines behavior for managing users (doctors, companies, etc.)."""

    @abstractmethod
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_user(self, user_id: str, patch: Dict[str, Any]) -> None:
        pass


class IClientService(ABC):
    """Defines behavior for managing clients (patients, customers, etc.)."""

    @abstractmethod
    def add_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        pass


class IInteractionService(ABC):
    """Defines behavior for managing interactions (visits, orders, calls, etc.)."""

    @abstractmethod
    def add_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_interactions(
        self, client_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_interaction(
        self, client_id: str, interaction_index: int, patch: Dict[str, Any]
    ) -> None:
        pass
