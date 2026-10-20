'''
binder_appointment.py
--------------------
interface for the appointments
'''

from datetime import date
from typing import List, Dict
from ..utils.normlize_user import normalize_user

def _appointment_book(user: Dict) -> Dict[str, List[Dict]]:
    """
    Return the user's appointments keyed by ISO date, creating it if needed.
    Accounts provisioned before this fix stored `appointments` as a list; treat that as empty.
    """
    meta = user.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        user["metadata"] = meta
    book = meta.get("appointments")
    if not isinstance(book, dict):
        book = {}
        meta["appointments"] = book
    return book


class AppointmentMixin:
    """
    Shared appointment logic for Business + Medical binders.
    Uses StorageAdapter through self.adapter.
    """
    
    def get_appointments(self, date: str) -> List[Dict]:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        appointments = _appointment_book(user).get(date, [])
        # ensure msg exists
        for a in appointments:
            a["msg"] = a.get("msg", "")
        return appointments

    def save_appointments(self, date: str, appointments: List[Dict]) -> None:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        _appointment_book(user)[date] = appointments
        self.adapter.update_user(self.domain,self.current_user, user)

    def lock_appointment(self, date: str, no: str) -> bool:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        book = _appointment_book(user)
        appointments = book.get(date, [])
        locked_any = False

        for ap in appointments:
            if str(ap.get("no")) == str(no):
                ap["locked"] = True
                locked_any = True

        if locked_any:
            book[date] = appointments
            self.adapter.update_user(self.domain,self.current_user, user)

        return locked_any
