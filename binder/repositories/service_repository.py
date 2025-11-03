"""
service_repository.py
--------------------
Repository for service data management.
"""

from typing import Dict, Any
from binder import Service,  BaseRepository


class ServiceRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "service", Service)

    def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        service = Service(**data)
        return self.create(service.to_dict())

    def get_services_for_user(self, user_id: str) -> list:
        return self.list(filters={"user_id": user_id})
