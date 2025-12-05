'''
binder_appointment.py
--------------------
interface for the appointments
'''

from typing import List, Dict

class IAppointment:
    """
    Shared appointment logic for Business + Medical binders.
    Uses StorageAdapter through self.adapter.
    """

    def get_appointments(self, date: str) -> List[Dict]:
        path = f"metadata/appointments/{date}"
        items = self.adapter.list_children(self.current_user, path)
        # ensure msg exists
        for a in items:
            a["msg"] = a.get("msg", "")
        return items

    def save_appointments(self, date: str, appointments: List[Dict]) -> None:
        path = f"metadata/appointments/{date}"
        # delete old list fully → replace with new
        existing = self.adapter.list_children(self.current_user, path)
        for a in existing:
            self.adapter.delete_child(self.current_user, path, a["id"])

        # write new children
        for ap in appointments:
            # if missing id → auto-generate
            if "id" not in ap or not ap["id"]:
                ap["id"] = self.adapter.add_child(self.current_user, path, ap)
            else:
                self.adapter.add_child(self.current_user, path, ap)

    def lock_appointment(self, no: str) -> bool:
        """
        Finds appointment by patient/client number.
        Marks: locked=True
        """
        all_dates = self.adapter.list_children(self.current_user, "appointments")
        locked_any = False

        for d in all_dates:
            date_key = d["id"]
            apps = self.adapter.list_children(self.current_user, f"appointments/{date_key}")

            for ap in apps:
                if str(ap.get("no")) == str(no):
                    self.adapter.update_child(
                        self.current_user,
                        f"appointments/{date_key}",
                        ap["id"],
                        {"locked": True}
                    )
                    locked_any = True

        return locked_any
