"""
storage_adapter.py
------------------------------
Abstract base class for data storage adapter. Implementations must be storage-agnostic.
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """
    Abstract base class describing minimal data operations used by binders.
    Implement this for any backend (SQLAlchemy, Mongo, Dynamo, S3, etc.).
    """

    @abstractmethod
    def update_user(self, domain: str, user_id: str, user_data: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get_user(self, domain: str, user_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete_user(self, domain: str, user_id: str) -> None:
        ...

    # Lists under a user: clients, employees, products, services
    @abstractmethod
    def list_children(self, domain: str, user_id: str, collection: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def add_child(self, domain: str, user_id: str, collection: str, obj: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    def update_child(self, domain: str, user_id: str, collection: str, child_id: str, patch: Dict[str, Any]) -> None:
        ...
    
    @abstractmethod
    def delete_child(self, domain: str, user_id: str, collection: str, child_id: str) -> None:
        ...

    # nested collections under child (interactions, transactions)
    @abstractmethod     
    def list_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def add_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, obj: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    def update_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, nested_id: str, patch: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, nested_id: str) -> None:
        ...

    @abstractmethod
    def find_children_by_field(self, domain: str, user_id: str, collection: str, field: str, value: Any) -> List[Dict]:
        """
        Return list of child documents under user_id/collection where child's field == value.
        Implementations should normalize / index where possible for efficiency.
        """
        ...