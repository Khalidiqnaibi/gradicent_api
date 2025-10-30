"""
Binder Medical
------------------
Concrete Binder implementation for any business type (product, service, or hybrid).
Includes full CRUD for users, clients, employees, products, services, interactions, and transactions.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .binder import Binder

class MedicalBinder(Binder):
    """Binder for the medical domain — manages doctors, patients, and visits."""
    ROOT = "/drs"

    # -------- USERS (Doctors) --------
    def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "google_id" not in data:
            raise ValueError("Doctor must include google_id")
        path = f"{self.ROOT}/{data['google_id']}"
        data.setdefault("created_at", datetime.utcnow().isoformat())
        data.setdefault("patients", [])
        return self._create(path, data)

    def read_user(self, google_id: str) -> Optional[Dict[str, Any]]:
        return self._read(f"{self.ROOT}/{google_id}")

    def update_user(self, google_id: str, patch: Dict[str, Any]) -> None:
        self._update(f"{self.ROOT}/{google_id}", patch)

    def delete_user(self, google_id: str) -> None:
        self._delete(f"{self.ROOT}/{google_id}")

    # -------- PATIENTS --------
    def create_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients"
        data.setdefault("id", str(int(datetime.utcnow().timestamp())))
        data.setdefault("visits", [])
        return self._create(path, data)

    def read_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        self._require_user()
        patients = self.adapter.get_list(f"{self.ROOT}/{self._current_user}/patients")
        return next((p for p in patients if str(p.get("id")) == str(patient_id)), None)

    def update_patient(self, patient_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients/{patient_id}"
        self._update(path, patch)

    def delete_patient(self, patient_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients/{patient_id}"
        self._delete(path)

    # -------- VISITS --------
    def create_visit(self, patient_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients/{patient_id}/visits"
        data.setdefault("vno", str(int(datetime.utcnow().timestamp())))
        data.setdefault("visit_date", datetime.utcnow().isoformat())
        return self._create(path, data)

    def read_visits(self, patient_id: str) -> List[Dict[str, Any]]:
        self._require_user()
        return self.adapter.get_list(f"{self.ROOT}/{self._current_user}/patients/{patient_id}/visits")

    def update_visit(self, patient_id: str, visit_id: str, patch: Dict[str, Any]) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients/{patient_id}/visits/{visit_id}"
        self._update(path, patch)

    def delete_visit(self, patient_id: str, visit_id: str) -> None:
        self._require_user()
        path = f"{self.ROOT}/{self._current_user}/patients/{patient_id}/visits/{visit_id}"
        self._delete(path)
