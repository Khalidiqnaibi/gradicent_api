"""
client_repository.py
--------------------
Repository for client data management.
"""

from typing import Dict, Any
from ..models.models import Client  
from ..interfaces.base_repository import BaseRepository


class ClientRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "clients", Client)

    def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        client = Client(**data)
        return self.create(client.to_dict())

    def get_clients_for_user(self, user_id: str) -> list:
        return self.list(filters={"user_id": user_id})
