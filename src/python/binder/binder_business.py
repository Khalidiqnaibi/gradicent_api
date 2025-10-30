"""
Binder Business
------------------
Concrete Binder implementation for any business type (product, service, or hybrid).
Includes full CRUD for users, clients, employees, products, services, interactions, and transactions.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .binder import Binder


def _ts() -> str:
    return datetime.now().isoformat()


class BinderBusiness(Binder):
    ROOT = "/Business"

    # -------- USERS CRUD --------
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in data:
            raise ValueError("User must have an 'id'")
        path = f"{self.ROOT}/{data['id']}"
        data.setdefault("created_at", _ts())
        data.setdefault("clients", [])
        data.setdefault("employees", [])
        data.setdefault("products", [])
        data.setdefault("services", [])
        self._create(path, data)
        return data

    def read(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self._read(f"{self.ROOT}/{entity_id}")

    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        self._update(f"{self.ROOT}/{entity_id}", patch)

    def delete(self, entity_id: str) -> None:
        self._delete(f"{self.ROOT}/{entity_id}")

    # -------- CLIENTS CRUD --------
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients"
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        data.setdefault("created_at", _ts())
        data.setdefault("interactions", [])
        data.setdefault("transactions", [])
        return self._create(path, data)

    def read_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        clients = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/clients")
        return next((c for c in clients if str(c.get("id")) == str(client_id)), None)

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}"
        self._update(path, patch)

    def delete_client(self, client_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}"
        self._delete(path)

    # -------- EMPLOYEES CRUD --------
    def create_employee(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/employees"
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        data.setdefault("created_at", _ts())
        return self._create(path, data)

    def read_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        emps = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/employees")
        return next((e for e in emps if str(e.get("id")) == str(employee_id)), None)

    def update_employee(self, employee_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/employees/{employee_id}"
        self._update(path, patch)

    def delete_employee(self, employee_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/employees/{employee_id}"
        self._delete(path)

    # -------- PRODUCTS CRUD --------
    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/products"
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        return self._create(path, data)

    def read_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        prods = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/products")
        return next((p for p in prods if str(p.get("id")) == str(product_id)), None)

    def update_product(self, product_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/products/{product_id}"
        self._update(path, patch)

    def delete_product(self, product_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/products/{product_id}"
        self._delete(path)

    # -------- SERVICES CRUD --------
    def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/services"
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        return self._create(path, data)

    def read_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        servs = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/services")
        return next((s for s in servs if str(s.get("id")) == str(service_id)), None)

    def update_service(self, service_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/services/{service_id}"
        self._update(path, patch)

    def delete_service(self, service_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/services/{service_id}"
        self._delete(path)

    # -------- INTERACTIONS CRUD --------
    def create_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        data.setdefault("timestamp", _ts())
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/interactions"
        return self._create(path, data)

    def list(self, client_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/interactions"
        interactions = self.adapter.get_list(path)
        if not filters:
            return interactions
        start, end = filters.get("from"), filters.get("to")
        if start or end:
            from datetime import datetime as dt
            start_dt = dt.fromisoformat(start) if start else None
            end_dt = dt.fromisoformat(end) if end else None
            return [
                i for i in interactions
                if (not start_dt or dt.fromisoformat(i["timestamp"]) >= start_dt)
                and (not end_dt or dt.fromisoformat(i["timestamp"]) <= end_dt)
            ]
        return interactions

    def update_interaction(self, client_id: str, interaction_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/interactions/{interaction_id}"
        self._update(path, patch)

    def delete_interaction(self, client_id: str, interaction_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/interactions/{interaction_id}"
        self._delete(path)

    # -------- TRANSACTIONS CRUD --------
    def create_transaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        data.setdefault("timestamp", _ts())
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/transactions"
        return self._create(path, data)

    def read_transaction(self, client_id: str, txn_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        txns = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/clients/{client_id}/transactions")
        return next((t for t in txns if str(t.get("id")) == str(txn_id)), None)

    def update_transaction(self, client_id: str, txn_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/transactions/{txn_id}"
        self._update(path, patch)

    def delete_transaction(self, client_id: str, txn_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/clients/{client_id}/transactions/{txn_id}"
        self._delete(path)
