"""
interaction_repository.py
-------------------------
Manages client interaction history.
"""

from typing import Dict, Any
from binder import Interaction,BaseRepository


class InteractionRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "interactions", Interaction)

    def get_for_client(self, client_id: str):
        return self.list(filters={"client_id": client_id})
