"""
Binder Medical
-----------------
Concrete implementation of Binder for the medical domain.

Manages:
 - Doctors (users)
 - Patients (clients)
 - Visits (interactions)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from binder import Binder


class MedicalBinder(Binder):
    """Concrete Binder for the medical domain."""

    ROOT_PATH = "/drs"

    # -------------------- USERS --------------------
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        if "google_id" not in user_data:
            raise ValueError("user_data must include 'google_id'")

        user_id = user_data["google_id"]
        user_data.setdefault("created_at", datetime.now().isoformat())
        user_data.setdefault("patients", [])
        self.adapter.set(f"{self.ROOT_PATH}/{user_id}", user_data)
        return user_data

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.get(f"{self.ROOT_PATH}/{user_id}")

    def update_user(self, user_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update(f"{self.ROOT_PATH}/{user_id}", patch)

    # -------------------- CLIENTS --------------------
    def add_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT_PATH}/{self._current_user}/patients"
        client_data.setdefault("visits", [])
        client_data.setdefault("id", int(datetime.now().timestamp()))
        self.adapter.push(path, client_data)
        return client_data

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        patients = self.adapter.get_list(f"{self.ROOT_PATH}/{self._current_user}/patients")
        for p in patients:
            if str(p.get("id")) == str(client_id) or p.get("name") == client_id:
                return p
        return None

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        base = f"{self.ROOT_PATH}/{self._current_user}/patients"
        patients = self.adapter.get(base)
        if not patients:
            return

        if isinstance(patients, dict):
            for key, p in patients.items():
                if str(p.get("id")) == str(client_id):
                    merged = {**p, **patch}
                    self.adapter.set_child_by_key(base, key, merged)
                    return

    # -------------------- INTERACTIONS --------------------
    def add_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        patient = self.get_client(client_id)
        if not patient:
            raise ValueError("Patient not found")

        data.setdefault("timestamp", datetime.now().isoformat())
        data.setdefault("vno", len(patient.get("visits", [])) + 1)
        patient["visits"].append(data)
        self.update_client(client_id, {"visits": patient["visits"]})
        return data

    def update_interaction(self, client_id: str, idx: int, patch: Dict[str, Any]) -> None:
        self._require_user()
        patient = self.get_client(client_id)
        if not patient:
            raise ValueError("Patient not found")

        visits = patient.get("visits", [])
        if idx >= len(visits):
            raise IndexError("Invalid visit index")
        visits[idx].update(patch)
        self.update_client(client_id, {"visits": visits})

    def get_interactions(self, client_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        patient = self.get_client(client_id)
        if not patient:
            return []
        visits = patient.get("visits", [])
        if not filters:
            return visits
        start, end = filters.get("from"), filters.get("to")
        if start or end:
            from datetime import datetime as dt
            start_dt = dt.fromisoformat(start) if start else None
            end_dt = dt.fromisoformat(end) if end else None
            return [
                v for v in visits
                if (not start_dt or dt.fromisoformat(v["visit_date"]) >= start_dt)
                and (not end_dt or dt.fromisoformat(v["visit_date"]) <= end_dt)
            ]
        return visits
