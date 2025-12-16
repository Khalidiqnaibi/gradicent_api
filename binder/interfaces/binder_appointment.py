'''
binder_appointment.py
--------------------
interface for the appointments
'''

from datetime import date
from typing import List, Dict
from ..utils.normlize_user import normalize_user

class IAppointment:
    """
    Shared appointment logic for Business + Medical binders.
    Uses StorageAdapter through self.adapter.
    """
    
    def get_appointments(self, date: str) -> List[Dict]:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        meta = user.get("metadata", {})
        appo = meta.get("appointments", {}) 
        appointments = appo.get(date, [])
        # ensure msg exists
        for a in appointments:
            a["msg"] = a.get("msg", "")
        return appointments

    def save_appointments(self, date: str, appointments: List[Dict]) -> None:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        if "metadata" not in user:
            user["metadata"] = {}
        if "appointments" not in user["metadata"]:
            user["metadata"]["appointments"] = {}
        user["metadata"]["appointments"][date] = appointments
        self.adapter.update_user(self.domain,self.current_user, user)

    def lock_appointment(self, date: str, no: str) -> bool:
        user = self.adapter.get_user(self.domain,self.current_user)
        user = normalize_user(user)
        user = user.to_dict() or {}
        appointments = user.get("metadata", {}).get("appointments", {}).get(date, [])
        locked_any = False

        for ap in appointments:
            if str(ap.get("no")) == str(no):
                ap["locked"] = True
                locked_any = True

        if locked_any:
            user["metadata"]["appointments"][date] = appointments
            self.adapter.update_user(self.domain,self.current_user, user)

        return locked_any
