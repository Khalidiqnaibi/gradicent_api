"""
Binder
---------------
Provides the BaseBinder class that composes the small service interfaces
and defines shared CRUD helpers for Firebase or similar adapters.
"""

from typing import Any, Dict, Optional , List 
from abc import ABC


class Binder(ABC):
    """Base class that other binders extend to interact with adapters and Gaia."""

    def __init__(self, adapter: Any, gaia_engine: Optional[Any] = None):
        if not adapter:
            raise ValueError("Adapter cannot be None")

        self._adapter = adapter
        self._gaia_engine = gaia_engine
        self._current_user: Optional[str] = None

    # --- Dependency Access ---
    @property
    def adapter(self) -> Any:
        return self._adapter

    @property
    def gaia_engine(self) -> Optional[Any]:
        return self._gaia_engine

    # --- Context Control ---
    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @current_user.setter
    def current_user(self, user_id: str) -> None:
        user = self._adapter.get_user(user_id)
        if not user:
            raise Exception(f"User {user_id} does not exist")
        self._current_user = user_id

    def _require_user(self) -> None:
        if not self._current_user:
            raise RuntimeError("Operation requires a logged-in user context")
        
    # interactions crud
    def create_interaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.adapter.add_nested(self.current_user, "clients", client_id, "interactions", data)
        return data
    
    def list_interactions(self, client_id: str) -> List[Dict[str, Any]]:
        return self.adapter.list_nested(self.current_user, "clients", client_id, "interactions")
    
    def update_interaction(self, client_id:str, interaction_no : int, patch:List[Any]) -> List[Any]:
        return self.adapter.update_nested(self.current_user, "clients", client_id, "interactions", interaction_no, patch)
       
    def delete_interaction(self, client_id:str, interaction_no:int)->None:
        self.adapter.delete_interaction(self.current_user,"clients", client_id, "interactions", interaction_no)