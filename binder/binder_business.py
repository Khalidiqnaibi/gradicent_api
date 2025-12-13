"""
Binder Business
------------------------------
BinderBusiness: storage-agnostic implementation using StorageAdapter.
All methods return / accept model dicts (uniform schema).
"""

from typing import Any, Dict, Optional , List
from .interfaces.storage_adapter import StorageAdapter
from .interfaces.binder import Binder
from .interfaces.binder_appointment import IAppointment
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
    IAppointment
):
    """
    Binder Business that stores and reads uniform model dicts.
    Uses StorageAdapter interface so any DB backend can be plugged.
    """

    # user CRUD
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_user(data["id"], data)
        self.current_user=data["id"]
        return data

    def read(self, entity_id: str) -> Dict[str, Any]:
        return self.adapter.get_user(entity_id)

    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        user = self.adapter.get_user(entity_id) or {}
        user.update(patch)
        self.adapter.update_user(entity_id, user)

    def delete(self, entity_id: str) -> None:
        self.adapter.delete_user(entity_id)

    # clients
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Fetch existing clients
        clients = self.adapter.get_child(self.current_user, "clients") or {}

        # The new id is simply the next index
        client_id = str(len(clients))

        # Insert id into the data before saving
        data["id"] = client_id

        # Save at /clients/<client_id>
        self.adapter.set_child(self.current_user, f"clients/{client_id}", data)

        return data

    def read_client(self, client_id: str) -> Dict[str, Any]:
        clients = self.adapter.list_children(self.current_user, "clients")
        client = clients[int(client_id)] 
        if client:
            return clients[int(client_id)] 
        else:
            return None

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(self.current_user, "clients", client_id, patch)

    def delete_client(self, client_id: str) -> None:
        self.adapter.delete_child(self.current_user, "clients", client_id)

    def search_clients(self, query: str) -> List[Dict[str, Any]]:
        """
        Domain-agnostic client search:
        - try gov_id exact (normalized)
        - try numeric id (index)
        - try phone (digits)
        - fallback to name substring
        """
        q = (query or "").strip()
        if not q:
            return []

        # helpers (small, explicit)
        def _norm_gov(x: str) -> str:
            import re
            return re.sub(r'[\s\-]', '', (x or '')).upper()

        def _digits(x: str) -> str:
            import re
            return re.sub(r'\D', '', (x or ''))

        # 1) gov id
        gov_norm = _norm_gov(q)
        if gov_norm:
            found = self.adapter.find_children_by_predicate(self.current_user, "clients", lambda c: _norm_gov(c.get("gov_id","")) == gov_norm)
            if found:
                return found

        # 2) numeric id (legacy: client stored as list index or 'id' field)
        if q.isdigit():
            # try exact id field first
            found = self.adapter.find_children_by_field(self.current_user, "clients", "id", q)
            if found:
                return found
            # fallback to index-based lookup (if adapter stores list)
            try:
                idx = int(q) - 1
                children = self.adapter.list_children(self.current_user, "clients")
                if 0 <= idx < len(children):
                    return [children[idx]]
            except Exception:
                pass

        # 3) phone match
        digits = _digits(q)
        if digits:
            found = self.adapter.find_by_phone(self.current_user, "clients", digits)
            if found:
                return found

        # 4) name substring
        found = self.adapter.find_by_name_substring(self.current_user, "clients", q)
        return found

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

    # transactions (nested)
    def create_transaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "clients", client_id, "transactions", data)
        return data

    def list_transactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "clients", client_id, "transactions")