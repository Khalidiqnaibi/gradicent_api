"""
storage_adapter.py
------------------------------
Adapter protocol for data storage. Implementations must be storage-agnostic.
"""

from typing import Any, Dict, List, Optional, Protocol


class StorageAdapter(Protocol):
    """
    Protocol describing minimal data operations used by binders.
    Implement this for any backend (SQLAlchemy, Mongo, Dynamo, S3, etc.).
    """

    def set_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
        ...

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        ...

    def delete_user(self, user_id: str) -> None:
        ...

    # Lists under a user: clients, employees, products, services
    def list_children(self, user_id: str, collection: str) -> List[Dict[str, Any]]:
        ...

    def add_child(self, user_id: str, collection: str, obj: Dict[str, Any]) -> str:
        ...

    def update_child(self, user_id: str, collection: str, child_id: str, patch: Dict[str, Any]) -> None:
        ...

    def delete_child(self, user_id: str, collection: str, child_id: str) -> None:
        ...

    # nested collections under child (interactions, transactions)
    def list_nested(self, user_id: str, collection: str, child_id: str, nested: str) -> List[Dict[str, Any]]:
        ...

    def add_nested(self, user_id: str, collection: str, child_id: str, nested: str, obj: Dict[str, Any]) -> str:
        ...

    def update_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str, patch: Dict[str, Any]) -> None:
        ...

    def delete_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str) -> None:
        ...

    def find_children_by_field(self, user_id: str, collection: str, field: str, value: Any) -> List[Dict]:
        """
        Return list of child documents under user_id/collection where child's field == value.
        Implementations should normalize / index where possible for efficiency.
        """
        ...