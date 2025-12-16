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
from .interfaces.binder_appointment import IAppointment


class BinderMedical(
    Binder, 
    IUserService, 
    IClientService, 
    IInteractionService,
    IAppointment
    ):
    """Medical domain binder."""
    
    def __init__(self, adapter, domain = "medical"):
        super().__init__(domain, adapter)

    # user
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_user(self.domain,data["id"], data)
        self.current_user=data["id"]
        return data

    def read(self, entity_id: str) -> Dict[str, Any]:
        return self.adapter.get_user(self.domain,entity_id)

    def update(self, entity_id: str, patch: Dict[str, Any]) -> None:
        user = self.adapter.get_user(self.domain,entity_id) or {}
        user.update(patch)
        self.adapter.update_user(self.domain,entity_id, user)

    def delete(self, entity_id: str) -> None:
        self.adapter.delete_user(self.domain,entity_id)

    # patient
    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clients = self.adapter.list_children(self.domain,self.current_user, "clients") or self.adapter.list_children(self.current_user, "patients")or {}
         
        client_id = str(len(clients))

        data["id"] = client_id

        self.adapter.add_child(self.domain,self.current_user, f"clients", data)

        return data

    def read_client(self, client_id: str) -> Dict[str, Any]:
        patients = self.adapter.list_children(self.domain,self.current_user, "clients") or self.adapter.list_children(self.current_user, "patients")
        client = patients[int(client_id)] 
        if client:
            return client
        else:
            return None

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_child(self.domain,self.current_user, "clients", client_id, patch) or self.adapter.update_child(self.current_user, "patients", client_id, patch)

    def delete_client(self, client_id: str) -> None:
        self.adapter.delete_child(self.domain,self.current_user, "clients", client_id) or self.adapter.delete_child(self.current_user, "patients", client_id)
        
    def search_clients(self, query: str) -> List[Dict[str, Any]]:
        """
        search over 'patients' collection for clients.
        """
        # reuse the same algorithm but target 'patients' collection
        q = (query or "").strip()
        if not q:
            return []

        import re
        def _norm_gov(x): return re.sub(r'[\s\-]', '', (x or '')).upper()
        def _digits(x): return re.sub(r'\D', '', (x or ''))

        gov_norm = _norm_gov(q)
        if gov_norm:
            found = self.adapter.find_children_by_predicate(self.domain,self.current_user, "clients", lambda c: _norm_gov(c.get("gov_id","")) == gov_norm) or self.adapter.find_children_by_predicate(self.current_user, "patients", lambda c: _norm_gov(c.get("gov_id","")) == gov_norm)
            if found: return found

        if q.isdigit():
            # id field
            found = self.adapter.find_children_by_field(self.domain,self.current_user, "clients", "id", q) or self.adapter.find_children_by_field(self.current_user, "patients", "id", q)
            if found: return found
            # numeric index
            try:
                idx = int(q) - 1
                children = self.adapter.list_children(self.domain,self.current_user, "clients") or self.adapter.list_children(self.current_user, "patients")
                if 0 <= idx < len(children):
                    return [children[idx]]
            except Exception:
                pass

        digits = _digits(q)
        if digits:
            found = self.adapter.find_by_phone(self.domain,self.current_user, "clients", digits) or self.adapter.find_by_phone(self.current_user, "patients", digits)
            if found: return found

        return self.adapter.find_by_name_substring(self.domain,self.current_user, "clients", q) or self.adapter.find_by_name_substring(self.current_user, "patients", q)

    # visits (nested)
    def create_interaction(self, patient_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.domain,self.current_user, "clients", patient_id, "visits", data) or self.adapter.add_nested(self.current_user, "patients", patient_id, "visits", data)
        return data

    def list_interactions(self, patient_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.domain,self.current_user, "clients", patient_id, "visits") or self.adapter.list_nested(self.current_user, "patients", patient_id, "visits")
    
    def update_interaction(self, patient_id: str, visit_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update_nested(self.domain,self.current_user, "clients", patient_id, "visits", visit_id, patch) or self.adapter.update_nested(self.current_user, "patients", patient_id, "visits", visit_id, patch)

    def delete_interaction(self, patient_id: str, visit_id: str) -> None:
        self.adapter.delete_nested(self.domain,self.current_user, "clients", patient_id, "visits", visit_id) or self.adapter.delete_nested(self.current_user, "patients", patient_id, "visits", visit_id)