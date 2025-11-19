"""
medical_binder.py
-----------------
Implements user (doctor), client (patient), and interaction (visit)
CRUD operations for the medical domain, using Firebase or similar adapters.
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from .interfaces.binder_interface import IUserService, IClientService, IInteractionService
from .interfaces.binder import Binder


class BinderMedical(Binder, IUserService, IClientService, IInteractionService):
    """Medical domain binder."""
    
    # user
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

    # patient
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._add_child("patients", data)

    def read_client(self, client_id: str) -> Dict[str, Any]:
        patients = self.adapter.list_children(self.current_user, "patients")
        return next((p for p in patients if p["id"] == client_id), None)

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(self.current_user, "patients", client_id, patch)

    def delete_client(self, client_id: str) -> None:
        self.adapter.delete_child(self.current_user, "patients", client_id)

    # visits (nested)
    def create_visit(self, patient_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "patients", patient_id, "visits", data)
        return data

    def list(self, patient_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "patients", patient_id, "visits")

    def update_visit(self, patient_id: str, visit_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_nested(self.current_user, "patients", patient_id, "visits", visit_id, patch)

    def delete_visit(self, patient_id: str, visit_id: str) -> None:
        self.adapter.delete_nested(self.current_user, "patients", patient_id, "visits", visit_id)