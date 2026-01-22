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
        clients = self.adapter.list_children(self.domain, self.current_user, "clients") or []
        client_id = str(len(clients))
        data["id"] = client_id
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "clients",
            data,
            client_id,
        )
        return data

    def read_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        clients = self.adapter.list_children(self.domain, self.current_user, "clients")
        try:
            return clients[int(client_id)]
        except Exception:
            return None

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

    def search_clients(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        def _norm_gov(x: str) -> str:
            import re
            return re.sub(r"[\s\-]", "", (x or "")).upper()

        def _digits(x: str) -> str:
            import re
            return re.sub(r"\D", "", (x or ""))

        gov_norm = _norm_gov(q)
        if gov_norm:
            found = self.adapter.find_children_by_predicate(
                self.domain,
                self.current_user,
                "clients",
                lambda c: _norm_gov(c.get("gov_id", "")) == gov_norm,
            )
            if found:
                return found

        if q.isdigit():
            if int(q) > 0:
                q = str(int(q) - 1)
                
            found = self.adapter.find_children_by_field(
                self.domain,
                self.current_user,
                "clients",
                "id",
                q,
            )
            if found:
                return found

        digits = _digits(q)
        if digits:
            found = self.adapter.find_by_phone(
                self.domain,
                self.current_user,
                "clients",
                digits,
            )
            if found:
                return found

        return self.adapter.find_by_name_substring(
            self.domain,
            self.current_user,
            "clients",
            q,
        )

# EMPLOYEES
class EmployeeMixin:
    def create_employee(self, data: Dict[str, Any]) -> Dict[str, Any]:
        employees = self.adapter.list_children(self.domain, self.current_user, "employees") or []
        employee_id = str(len(employees))
        data["id"] = employee_id
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "employees",
            data,
            employee_id,
        )
        return data

    def read_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        employees = self.adapter.list_children(self.domain, self.current_user, "employees")
        try:
            return employees[int(employee_id)]
        except Exception:
            return None
        
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

# PRODUCTS
class ProductMixin:
    def create_products(self, data: Dict[str, Any]) -> Dict[str, Any]:
        products = self.adapter.list_children(self.domain, self.current_user, "products") or []
        product_id = str(len(products))
        data["id"] = product_id
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "products",
            data,
            product_id,
        )
        return data

    def read_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        products = self.adapter.list_children(self.domain, self.current_user, "products")
        try:
            return products[int(product_id)]
        except Exception:
            return None

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

# SERVICES
class ServiceMixin:
    def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        services = self.adapter.list_children(self.domain, self.current_user, "services") or []
        service_id = str(len(services))
        data["id"] = service_id
        self.adapter.update_child(
            self.domain,
            self.current_user,
            "services",
            data,
            service_id,
        )
        return data

    def read_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        services = self.adapter.list_children(self.domain, self.current_user, "services")
        try:
            return services[int(service_id)]
        except Exception:
            return None

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

    def list_interactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "interactions",
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

    def list_transactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(
            self.domain,
            self.current_user,
            "clients",
            client_id,
            "transactions",
        )
