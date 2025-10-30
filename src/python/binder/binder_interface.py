"""
Binder Interface
---
Defines abstract interfaces for CRUD operations used by the Binder system.
Implements SOLID principles by separating concerns clearly.

Follows the Interface Segregation and Dependency Inversion principles.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ICrudService(ABC):
    """Generic CRUD interface."""

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> None:
        pass


class IUserService(ICrudService, ABC):
    pass


class IClientService(ICrudService, ABC):
    pass


class IEmployeeService(ICrudService, ABC):
    pass


class IProductService(ICrudService, ABC):
    pass


class IServiceService(ICrudService, ABC):
    pass


class IInteractionService(ICrudService, ABC):
    """Interaction CRUD includes filtering."""
    
    @abstractmethod
    def list(self, client_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        pass


class ITransactionService(ICrudService, ABC):
    pass
