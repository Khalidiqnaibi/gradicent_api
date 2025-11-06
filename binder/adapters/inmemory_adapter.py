"""
In Memory Adapter
---------------------------------------
Simple, thread-unsafe in-memory adapter for development and testing.
"""

from typing import Any, Dict, List, Optional
import uuid

from ..interfaces.storage_adapter import StorageAdapter


def _new_id() -> str:
    return uuid.uuid4().hex


class InMemoryAdapter(StorageAdapter):
    def __init__(self) -> None:
        '''
        storage structure:
        users: { user_id: {user_data} }
        children stored as lists inside user_data for simplicity
        '''
        self.users: Dict[str, Dict[str, Any]] = {}

    # User methods
    def set_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
        self.users[user_id] = dict(user_data)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)

    def delete_user(self, user_id: str) -> None:
        self.users.pop(user_id, None)

    # Children lists (clients, employees, products, services)
    def list_children(self, user_id: str, collection: str) -> List[Dict[str, Any]]:
        user = self.users.get(user_id, {})
        return list(user.get(collection, []))

    def add_child(self, user_id: str, collection: str, obj: Dict[str, Any]) -> str:
        obj = dict(obj)
        obj_id = obj.get("id") or _new_id()
        obj["id"] = str(obj_id)
        user = self.users.setdefault(user_id, {})
        coll = user.setdefault(collection, [])
        coll.append(obj)
        return obj["id"]

    def update_child(self, user_id: str, collection: str, child_id: str, patch: Dict[str, Any]) -> None:
        user = self.users.get(user_id, {})
        coll = user.get(collection, [])
        for i, item in enumerate(coll):
            if str(item.get("id")) == str(child_id):
                merged = dict(item)
                merged.update(patch)
                coll[i] = merged
                return
        raise KeyError(f"{collection} child {child_id} not found")

    def delete_child(self, user_id: str, collection: str, child_id: str) -> None:
        user = self.users.get(user_id, {})
        coll = user.get(collection, [])
        user[collection] = [i for i in coll if str(i.get("id")) != str(child_id)]

    # Nested operations (interactions, transactions)
    def list_nested(self, user_id: str, collection: str, child_id: str, nested: str) -> List[Dict[str, Any]]:
        child = next((c for c in self.list_children(user_id, collection) if str(c.get("id")) == str(child_id)), None)
        if not child:
            return []
        return list(child.get(nested, []))

    def add_nested(self, user_id: str, collection: str, child_id: str, nested: str, obj: Dict[str, Any]) -> str:
        child = next((c for c in self.list_children(user_id, collection) if str(c.get("id")) == str(child_id)), None)
        if child is None:
            raise KeyError("parent not found")
        obj = dict(obj)
        nid = obj.get("id") or _new_id()
        obj["id"] = str(nid)
        lst = child.setdefault(nested, [])
        lst.append(obj)
        return obj["id"]

    def update_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str, patch: Dict[str, Any]) -> None:
        child = next((c for c in self.list_children(user_id, collection) if str(c.get("id")) == str(child_id)), None)
        if child is None:
            raise KeyError("parent not found")
        lst = child.get(nested, [])
        for i, item in enumerate(lst):
            if str(item.get("id")) == str(nested_id):
                merged = dict(item)
                merged.update(patch)
                lst[i] = merged
                return
        raise KeyError("nested item not found")

    def delete_nested(self, user_id: str, collection: str, child_id: str, nested: str, nested_id: str) -> None:
        child = next((c for c in self.list_children(user_id, collection) if str(c.get("id")) == str(child_id)), None)
        if child is None:
            return
        child[nested] = [i for i in child.get(nested, []) if str(i.get("id")) != str(nested_id)]
