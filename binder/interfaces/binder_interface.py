"""
binder_interfaces.py
--------------------
Defines unified abstract interfaces for all Binder domains (Business, Medical, etc.)
Implements full CRUD contracts following SOLID principles:
- SRP: Each interface defines only its own domain responsibility.
- OCP: New entity types can be added via subclassing.
- LSP: Concrete classes can replace abstract ones transparently.
- ISP: Segregated interfaces via specialization of ICrudService.
- DIP: High-level modules depend on abstractions, not storage details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# -------------------- Base CRUD Contract --------------------
class ICrudService(ABC):
    """Generic CRUD interface for all entities."""

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        pass

    @abstractmethod
    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Read a single entity by ID."""
        pass

    @abstractmethod
    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        """Apply partial updates to an entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> None:
        """Delete an entity."""
        pass

# -------------------- Nested CRUD Contract --------------------
class INestedCrudService(ICrudService):
    """CRUD interface for nested entities (e.g., visits, interactions)."""

    @abstractmethod
    def list(self, parent_id: str) -> List[Dict[str, Any]]:
        """List all nested entities for a parent entity."""
        pass

# -------------------- Domain-Specific Interfaces --------------------
class IUserService(ICrudService):
    """User management (doctors, organizations, etc.)."""
    pass

class IClientService(ICrudService):
    """Clients or patients depending on Binder domain."""
    pass

class IEmployeeService(ICrudService):
    """Employees, staff, or collaborators."""
    pass

class IProductService(ICrudService):
    """Products offered by a business."""
    pass

class IServiceService(ICrudService):
    """Services offered by a business or medical practice."""
    pass

class IInteractionService(ABC):
    """Interactions or communications tied to a client/patient."""
    @abstractmethod
    def create_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "clients", client_id, "interactions", data)
        return data
    
    @abstractmethod
    def list_interactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "clients", client_id, "interactions")
    
    @abstractmethod
    def update_interaction(self, client_id:str, interaction_no : int, patch:List[Any]) -> List[Any]:
        return self.adapter.update_nested(self.current_user, "clients", client_id, "interactions", interaction_no, patch)
    
    @abstractmethod
    def delete_interaction(self, client_id:str, interaction_no:int)->None:
        self.adapter.delete_interaction(self.current_user,"clients", client_id, "interactions", interaction_no)

class ITransactionService():
    """Transactions or payments tied to a client/patient."""
    pass