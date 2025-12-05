"""
appointments_service.py
-----------------------
SOLID service for appointment storage.

Responsibilities:
- NEVER talk to Firebase directly
- Use the StorageAdapter (FirebaseCrudAdapter)
- Provide clean CRUD for date-based appointment lists
"""

from typing import List, Dict, Any


class AppointmentsService:
    def __init__(self, storage_adapter, collection_name="appointments"):
        self.storage = storage_adapter
        self.collection = collection_name

    # -----------------------------------------
    # READ appointments for a specific date
    # -----------------------------------------
    def get_appointments(self, user_id: str, date: str) -> List[Dict]:
        all_dates = self.storage.list_children(user_id, self.collection)

        # match exact date inside children
        for d in all_dates:
            if d["id"] == date:
                return d.get("items", [])

        return []

    # -----------------------------------------
    # SAVE appointments for a specific date
    # Overwrites ONLY that date
    # -----------------------------------------
    def save_appointments(self, user_id: str, date: str, appointments: List[Dict]) -> None:
        payload = {"id": date, "items": appointments}
        self.storage.add_child(user_id, self.collection, payload)

    # -----------------------------------------
    # LOCK appointment that matches number “no”
    # -----------------------------------------
    def lock_appointment(self, user_id: str, no: int) -> None:
        all_dates = self.storage.list_children(user_id, self.collection)

        changed = False

        for d in all_dates:
            items = d.get("items", [])
            for appt in items:
                if appt.get("no") == no:
                    appt["locked"] = True
                    changed = True
            if changed:
                self.storage.add_child(user_id, self.collection, {
                    "id": d["id"],
                    "items": items
                })
