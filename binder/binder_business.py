"""
Binder Business
------------------------------
BinderBusiness: storage-agnostic implementation using StorageAdapter.
All methods return / accept model dicts (uniform schema).
"""

from typing import Any, Dict, Optional , List
from .interfaces.storage_adapter import StorageAdapter
from .interfaces.binder import Binder
from .interfaces.binder_interface import (
    IUserService,
    IClientService,
    IEmployeeService,
    IProductService,
    IServiceService,
    IInteractionService,
    ITransactionService,
)

class BinderBusiness(
    Binder,
    IUserService,
    IClientService,
    IEmployeeService,
    IProductService,
    IServiceService,
    IInteractionService,
    ITransactionService,
):
    """
    Binder Business that stores and reads uniform model dicts.
    Uses StorageAdapter interface so any DB backend can be plugged.
    """

    # user CRUD
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.set_user(data["id"], data)
        self.current_user=data["id"]
        return data

    def read(self, entity_id: str) -> Dict[str, Any]:
        return self.adapter.get_user(entity_id)

    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        user = self.adapter.get_user(entity_id) or {}
        user.update(patch)
        self.adapter.set_user(entity_id, user)

    def delete(self, entity_id: str) -> None:
        self.adapter.delete_user(entity_id)

    # clients
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._add_child("clients", data)

    def read_client(self, client_id: str) -> Dict[str, Any]:
        return next(
            (c for c in self.adapter.list_children(self.current_user, "clients") if c["id"] == client_id),
            None,
        )

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(self.current_user, "clients", client_id, patch)

    def delete_client(self, client_id: str) -> None:
        self.adapter.delete_child(self.current_user, "clients", client_id)

    # employees, products, services (same structure)
    def create_employee(self, data): return self._add_child("employees", data)
    def update_employee(self, emp_id, patch): self.adapter.update_child(self.current_user, "employees", emp_id, patch)
    def delete_employee(self, emp_id): self.adapter.delete_child(self.current_user, "employees", emp_id)

    def create_product(self, data): return self._add_child("products", data)
    def update_product(self, prod_id, patch): self.adapter.update_child(self.current_user, "products", prod_id, patch)
    def delete_product(self, prod_id): self.adapter.delete_child(self.current_user, "products", prod_id)

    def create_service(self, data): return self._add_child("services", data)
    def update_service(self, svc_id, patch): self.adapter.update_child(self.current_user, "services", svc_id, patch)
    def delete_service(self, svc_id): self.adapter.delete_child(self.current_user, "services", svc_id)

    # interactions / transactions (nested)
    def create_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "clients", client_id, "interactions", data)
        return data

    def list(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "clients", client_id, "interactions")

    def create_transaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "clients", client_id, "transactions", data)
        return data

    def list_transactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "clients", client_id, "transactions")