"""
base_repository.py
------------------
Defines BaseRepository that wraps a StorageAdapter for CRUD operations.
All repositories inherit from this.
"""

from typing import Any, Dict, List, Optional, Type
from binder.interfaces.storage_adapter import StorageAdapter


class BaseRepository:
    """
    Generic repository that delegates CRUD to the StorageAdapter.
    """

    def __init__(self, adapter: StorageAdapter, collection_name: str, model_class: Optional[Type] = None):
        self.adapter = adapter
        self.collection = collection_name
        self.model_class = model_class

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record_id = self.adapter.create(self.collection, data)
        return self.read(record_id)

    def read(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.adapter.read(self.collection, record_id)

    def update(self, record_id: str, patch: Dict[str, Any]) -> None:
        self.adapter.update(self.collection, record_id, patch)

    def delete(self, record_id: str) -> None:
        self.adapter.delete(self.collection, record_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.adapter.list(self.collection, filters)
