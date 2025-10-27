"""
Binder Business
------------------
Concrete implementation of Binder for general business domain.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from binder import Binder


class BusinessBinder(Binder):
    """Concrete Binder for managing companies, clients, and interactions."""

    ROOT_PATH = "/Busines"

    # -------------------- USERS --------------------
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in user_data:
            raise ValueError("user_data must include 'id'")

        user_id = user_data["id"]
        user_data.setdefault("created_at", datetime.now().isoformat())
        user_data.setdefault("clients", [])
        self.adapter.set(f"{self.ROOT_PATH}/{user_id}", user_data)
        return user_data

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get(f"{self.ROOT_PATH}/{user_id}")

    def update_user(self, user_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update(f"{self.ROOT_PATH}/{user_id}", patch)

    # -------------------- CLIENTS --------------------
    def add_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT_PATH}/{self._current_user}/clients"
        client_data.setdefault("interactions", [])
        client_data.setdefault("id", int(datetime.now().timestamp()))
        self.adapter.push(path, client_data)
        return client_data

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        clients = self.adapter.get_list(f"{self.ROOT_PATH}/{self._current_user}/clients")
        for c in clients:
            if str(c.get("id")) == str(client_id) or c.get("name") == client_id:
                return c
        return None

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        base = f"{self.ROOT_PATH}/{self._current_user}/clients"
        clients = self.adapter.get(base)
        if not clients:
            return

        if isinstance(clients, dict):
            for key, c in clients.items():
                if str(c.get("id")) == str(client_id):
                    merged = {**c, **patch}
                    self.adapter.set_child_by_key(base, key, merged)
                    return

    # -------------------- INTERACTIONS --------------------
    def add_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        client = self.get_client(client_id)
        if not client:
            raise ValueError("Client not found")

        data.setdefault("timestamp", datetime.now().isoformat())
        data.setdefault("ino", len(client.get("interactions", [])) + 1)
        client["interactions"].append(data)
        self.update_client(client_id, {"interactions": client["interactions"]})
        return data

    def update_interaction(self, client_id: str, idx: int, patch: Dict[str, Any]) -> None:
        self._require_user()
        client = self.get_client(client_id)
        if not client:
            raise ValueError("Client not found")

        interactions = client.get("interactions", [])
        if idx >= len(interactions):
            raise IndexError("Invalid interaction index")
        interactions[idx].update(patch)
        self.update_client(client_id, {"interactions": interactions})

    def get_interactions(self, client_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        client = self.get_client(client_id)
        if not client:
            return []
        interactions = client.get("interactions", [])
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
