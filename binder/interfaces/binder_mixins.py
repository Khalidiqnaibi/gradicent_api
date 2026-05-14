"""
binder_mixins.py
----------------
Reusable mixins that implement Binder domain behavior.

Design:
- Mixins contain ALL logic
- No abstract base classes
- Duck-typing friendly
- Optional typing via Protocols (for IDEs & MyPy)
"""

from typing import Any, Dict, List, Optional, Protocol


# Shared structural typing (OPTIONAL, SAFE)
class HasBinderContext(Protocol):
    adapter: Any
    domain: str
    current_user: str

# USER (ROOT ENTITY)
class UserMixin:
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_user(self.domain, data["id"], data)
        self.current_user = data["id"]
        return data

    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_user(self.domain, entity_id)

    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        user = self.read(entity_id) or {}
        user.update(patch)
        self.adapter.update_user(self.domain, entity_id, user)

    def delete(self, entity_id: str) -> None:
        self.adapter.delete_user(self.domain, entity_id)

# CLIENTS / PATIENTS
class ClientMixin:
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_child(
            self.domain,
            self.current_user,
            "clients",
            data,
        )
        return data

    def read_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, "clients", client_id
        )
    
    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "clients",
            patch,
            client_id,
        )

    def delete_client(self, client_id: str) -> None:
        self.adapter.delete_child(
            self.domain,
            self.current_user,
            "clients",
            client_id,
        )

    # NEW: Optimized for Supabase SQL
    def search_clients(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        # 1. Search by Gov ID
        found = self.adapter.find_by_gov_id(self.domain, self.current_user, "clients", q)
        if found:
            return found

        # 2. Search by Numeric ID
        if q.isdigit():
            target_id = str(int(q) - 1) if int(q) > 0 else q
            found = self.adapter.find_children_by_field(self.domain, self.current_user, "clients", "id", target_id)
            if found:
                return found

        # 3. Search by Phone
        found = self.adapter.find_by_phone(self.domain, self.current_user, "clients", q)
        if found:
            return found

        # 4. Search by Name Substring 
        return self.adapter.find_by_name_substring(self.domain, self.current_user, "clients", q)

# EMPLOYEES
class EmployeeMixin:
    def create_employee(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_child(
            self.domain,
            self.current_user,
            "employees",
            data,
        )
        return data

    def read_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, "employees", employee_id
        )
        
    def update_employee(self, emp_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "employees",
            patch,
            emp_id,
        )

    def delete_employee(self, emp_id: str) -> None:
        self.adapter.delete_child(
            self.domain,
            self.current_user,
            "employees",
            emp_id,
        )

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        # search by id
        if q.isdigit():
            found = self.adapter.find_children_by_field(
                self.domain,
                self.current_user,
                "employees",
                "id",
                q,
            )
            if found:
                return found

        # search by exact role
        found = self.adapter.find_children_by_field(
            self.domain, 
            self.current_user, 
            "employees", 
            "role", 
            q.lower()
        )
        if found:
            return found

        # fallback to name substring
        return self.adapter.find_by_name_substring(
            self.domain,
            self.current_user,
            "employees",
            q,
        )

# PRODUCTS
class ProductMixin:
    def create_products(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_child(
            self.domain,
            self.current_user,
            "products",
            data,
        )
        return data

    def read_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, "products", product_id
        )

    def update_product(self, prod_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "products",
            patch,
            prod_id,
        )

    def delete_product(self, prod_id: str) -> None:
        self.adapter.delete_child(
            self.domain,
            self.current_user,
            "products",
            prod_id,
        )

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        # search by id
        if q.isdigit():
            found = self.adapter.find_children_by_field(
                self.domain,
                self.current_user,
                "products",
                "id",
                q,
            )
            if found:
                return found

        # search by sku in metadata
        found = self.adapter.find_children_by_nested_field(
            self.domain, 
            self.current_user, 
            "products", 
            "metadata", 
            "sku", 
            q.lower()
        )
        if found:
            return found

        # fallback to name substring
        return self.adapter.find_by_name_substring(
            self.domain,
            self.current_user,
            "products",
            q,
        )

# SERVICES
class ServiceMixin:
    def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_child(
            self.domain,
            self.current_user,
            "services",
            data,
        )
        return data

    def read_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, "services", service_id
        )

    def update_service(self, svc_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "services",
            patch,
            svc_id,
        )

    def delete_service(self, svc_id: str) -> None:
        self.adapter.delete_child(
            self.domain,
            self.current_user,
            "services",
            svc_id,
        )

    def search_services(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        # search by id
        if q.isdigit():
            found = self.adapter.find_children_by_field(
                self.domain,
                self.current_user,
                "services",
                "id",
                q,
            )
            if found:
                return found

        # fallback to name substring
        return self.adapter.find_by_name_substring(
            self.domain,
            self.current_user,
            "services",
            q,
        )

# INTERACTIONS (NESTED)
class InteractionMixin:
    def create_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "interactions",
            data,
        )
        return data

    def list_interactions(self, client_id: str, start_at:str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "interactions", 
            start_at
        )

    def update_interaction(
        self,
        client_id: str,
        interaction_no: int,
        patch: List[Any],
    ) -> List[Any]:
        return self.adapter.update_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "interactions",
            interaction_no,
            patch,
        )

    def delete_interaction(self, client_id: str, interaction_no: int) -> None:
        self.adapter.delete_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "interactions",
            interaction_no,
        )

    def read_interaction(self, client_id: str, interaction_no: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, f"clients/{client_id}/interactions", interaction_no
        )


# TRANSACTIONS
class TransactionMixin:
    def create_transaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "transactions",
            data,
        )
        return data

    def list_transactions(self, client_id: str,start_at:str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "transactions",
            start_at
        )

    def update_transaction(
        self,
        client_id: str,
        transaction_no: int,
        patch: List[Any],
    ) -> List[Any]:
        return self.adapter.update_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "transactions",
            transaction_no,
            patch,
        )

    def delete_transaction(self, client_id: str, transaction_no: int) -> None:
        self.adapter.delete_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "transactions",
            transaction_no,
        )

    def read_transaction(self, client_id: str, transaction_no: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get_child(
            self.domain, self.current_user, f"clients/{client_id}/transactions", transaction_no
        )

