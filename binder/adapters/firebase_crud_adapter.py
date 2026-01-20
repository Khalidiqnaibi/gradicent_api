"""
firebase_crud_adapter.py
------------------------
Firebase implementation of the StorageAdapter with full search support:
- gov_id exact (normalized)
- phone exact (digits)
- name substring (lowercase)
- id / index fallback
"""

from importlib.resources import path
from typing import Any, Dict, List, Optional
from firebase_admin import db
from ..interfaces.storage_adapter import StorageAdapter
import re 

def normalize_digits(s: str) -> str:
    """Remove all non-digits."""
    return re.sub(r"\D", "", s or "")


def normalize_gov_id(s: str) -> str:
    """Uppercase GOV ID, remove spaces and dashes."""
    return re.sub(r"[\s\-]", "", (s or "")).upper()


class FirebaseCrudAdapter(StorageAdapter):
    def __init__(self, root_path: str = "users"):
        self.root_path = root_path

    # --------------------
    # Base references
    # --------------------
    def _user_ref(self, user_id: str):
        return db.reference(f"/{self.root_path}/{user_id}")

    def _child_ref(self, user_id: str, collection: str, child_id: Optional[str] = None):
        ref = db.reference(f"/{self.root_path}/{user_id}/{collection}")
        return ref if not child_id else ref.child(child_id)

    def _nested_ref(
        self,
        user_id: str,
        collection: str,
        child_id: str,
        nested: str,
        nested_id: Optional[str] = None,
    ):
        ref = db.reference(f"/{self.root_path}/{user_id}/{collection}/{child_id}/{nested}")
        return ref if not nested_id else ref.child(str(nested_id))

    # --------------------
    # User CRUD
    # --------------------
    def add_user(self, user_id: str, user: Dict) -> None:
        self._user_ref(user_id).set(user)

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self._user_ref(user_id).get()

    def update_user(self, user_id: str, user: Dict) -> None:
        self._user_ref(user_id).set(user)

    def delete_user(self, user_id: str) -> None:
        self._user_ref(user_id).delete()

    # --------------------
    # Child CRUD
    # --------------------
    def list_children(self, user_id: str, collection: str) -> List[Dict]:
        ref = self._child_ref(user_id, collection)
        children = ref.get() or {}

        if isinstance(children, list):
            children = {str(i): v for i, v in enumerate(children)}

        result = []
        for k, v in children.items():
            if isinstance(v, dict):
                result.append({"id": k, **v})
            else:
                result.append({"id": k, "value": v})

        return result

    def add_child(self, user_id: str, collection: str, obj: Dict) -> str:
        child_id = obj.get("id")
        if not child_id:
            # push() auto-generated ID
            ref = self._child_ref(user_id, collection).push(obj)
            child_id = ref.key
            ref.update({"id": child_id})
            return child_id

        self._child_ref(user_id, collection, child_id).set(obj)
        return child_id

    def update_child(self, user_id: str, collection: str, child_id: str, patch: Dict) -> None:
        self._child_ref(user_id, collection, child_id).update(patch)

    def delete_child(self, user_id: str, collection: str, child_id: str) -> None:
        self._child_ref(user_id, collection, child_id).delete()

    # --------------------
    # Nested CRUD
    # --------------------
    def list_nested(self, user_id: str, collection: str, child_id: str, nested: str) -> List[Dict]:
        ref = self._nested_ref(user_id, collection, child_id, nested)
        nested_objs = ref.get() or {}

        if isinstance(nested_objs, list):
            nested_objs = {str(i): v for i, v in enumerate(nested_objs)}

        result = []
        for k, v in nested_objs.items():
            if isinstance(v, dict):
                result.append({"id": k, **v})
            else:
                result.append({"id": k, "value": v})

        return result

    def add_nested(self, domain :str, user_id: str, collection: str, child_id: str, nested: str, obj: Dict) -> str:
        ref = self._nested_ref(user_id, collection, child_id, nested)
        content = ref.get()
        print(content)
        if isinstance(content,list) :
            nested_id = len(content)
        elif content and content.get("vno"):
            nested_id = 1
            interactions = {'0':content,'1':obj}
            ref.push(interactions)
            return nested_id
        else:
            nested_id = 0
            interactions = {'0':obj}

        full_ref = self._nested_ref(user_id,collection,child_id,nested,str(nested_id)).push(obj)
        
        return nested_id

    def update_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str, patch: Dict) -> None:
        ref = self._nested_ref(user_id, collection, child_id, nested, nested_id)
        content = ref.get()
        if isinstance(content,list) :
            new = {str(i): v for i, v in enumerate(content)}
        else:
            new = content
        index = len(new)
        new[index] = patch
        ref.update(new)

    def delete_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str) -> None:
        self._nested_ref(user_id, collection, child_id, nested, nested_id).delete()

    # SEARCH SUPPORT (Gov ID, Phone, Name, ID)
    
    # --- exact match on field ---
    def find_children_by_field(self, user_id: str, collection: str, field: str, value: Any) -> List[Dict]:
        all_children = self.list_children(user_id, collection)
        return [c for c in all_children if c.get(field) == value]

    # --- gov id match (normalized) ---
    def find_by_gov_id(self, user_id: str, collection: str, gov_id: str) -> List[Dict]:
        target = normalize_gov_id(gov_id)
        all_children = self.list_children(user_id, collection)
        return [
            c for c in all_children
            if normalize_gov_id(c.get("gov_id", "")) == target
        ]

    # --- phone match (digits-only) ---
    def find_by_phone(self, user_id: str, collection: str, phone: str) -> List[Dict]:
        target = normalize_digits(phone)
        all_children = self.list_children(user_id, collection)
        return [
            c for c in all_children
            if normalize_digits(c.get("phone", "")) == target
        ]

    # --- name substring match (slow but simple) ---
    def find_by_name_substring(self, user_id: str, collection: str, name: str) -> List[Dict]:
        q = (name or "").lower()
        all_children = self.list_children(user_id, collection)
        return [
            c for c in all_children
            if q in (c.get("name", "") or "").lower()
        ]

    # --- predicate generic ---
    def find_children_by_predicate(self, user_id: str, collection: str, predicate) -> List[Dict]:
        all_children = self.list_children(user_id, collection)
        return [c for c in all_children if predicate(c)]
