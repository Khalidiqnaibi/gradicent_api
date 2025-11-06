"""
firebase_crud_adapter.py
------------------------
Implements FirebaseCrudAdapter, a concrete StorageAdapter for
Binder systems (Business, Medical, etc.).

Follows company standards:
- Readability over cleverness.
- Consistency and clarity in data flow.
- Explicit CRUD for top-level, child, and nested data.
"""

from typing import Any, Dict, List, Optional
from firebase_admin import db
from ..interfaces.storage_adapter import StorageAdapter


class FirebaseCrudAdapter(StorageAdapter):
    """
    Firebase implementation of the StorageAdapter interface.

    Structure example:
    /users/{user_id}
        /clients/{client_id}
            /transactions/{txn_id}
            /interactions/{int_id}
        /employees/{emp_id}
        /products/{prod_id}
        /services/{svc_id}
    """

    def __init__(self, root_path: str = "users"):
        """
        Args:
            root_path (str): Root path in Firebase where users are stored.
        """
        self.root_path = root_path

    # Helpers
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
        return ref if not nested_id else ref.child(nested_id)

    # User-level operations
    def add_user(self, user_id: str, user: Dict) -> None:
        """Create or replace a user entry."""
        self._user_ref(user_id).set(user)

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Retrieve user data."""
        return self._user_ref(user_id).get()

    def update_user(self, user_id: str, user: Dict) -> None:
        """Create or replace a user entry."""
        self._user_ref(user_id).set(user)

    def delete_user(self, user_id: str) -> None:
        """Remove a user and all related data."""
        self._user_ref(user_id).delete()

    # Child-level operations
    def list_children(self, user_id: str, collection: str) -> List[Dict]:
        """Return all child objects under a given collection."""
        ref = self._child_ref(user_id, collection)
        children = ref.get() or {}
        return [dict({"id": k}, **v) if isinstance(v, dict) else {"id": k, "value": v} for k, v in children.items()]

    def add_child(self, user_id: str, collection: str, obj: Dict) -> str:
        """Add a new child object (e.g., client, product)."""
        ref = self._child_ref(user_id, collection).push(obj)
        child_id = ref.key
        ref.update({"id": child_id})
        return child_id

    def update_child(self, user_id: str, collection: str, child_id: str, patch: Dict) -> None:
        """Update a child object partially."""
        self._child_ref(user_id, collection, child_id).update(patch)

    def delete_child(self, user_id: str, collection: str, child_id: str) -> None:
        """Delete a child object."""
        self._child_ref(user_id, collection, child_id).delete()

    # Nested-level operations (e.g., visits, interactions, transactions)
    def list_nested(self, user_id: str, collection: str, child_id: str, nested: str) -> List[Dict]:
        """Return all nested objects under a specific child."""
        ref = self._nested_ref(user_id, collection, child_id, nested)
        nested_objs = ref.get() or {}
        return [
            dict({"id": k}, **v) if isinstance(v, dict) else {"id": k, "value": v}
            for k, v in nested_objs.items()
        ]

    def add_nested(
        self,
        user_id: str,
        collection: str,
        child_id: str,
        nested: str,
        obj: Dict,
    ) -> str:
        """Add a nested object (e.g., a visit under a patient)."""
        ref = self._nested_ref(user_id, collection, child_id, nested).push(obj)
        nested_id = ref.key
        ref.update({"id": nested_id})
        return nested_id

    def update_nested(
        self,
        user_id: str,
        collection: str,
        child_id: str,
        nested: str,
        nested_id: str,
        patch: Dict,
    ) -> None:
        """Update a nested object."""
        self._nested_ref(user_id, collection, child_id, nested, nested_id).update(patch)

    def delete_nested(
        self,
        user_id: str,
        collection: str,
        child_id: str,
        nested: str,
        nested_id: str,
    ) -> None:
        """Delete a nested object."""
        self._nested_ref(user_id, collection, child_id, nested, nested_id).delete()
