# medical_service.py
from gaia.engine import GaiaEngine
from medical_binder import MedicalBinder
from gaia.adapters.firebase_crud_adapter import FirebaseCrudAdapter


class MedicalService:
    """Connects MedicalBinder with GaiaEngine analytics."""

    def __init__(self):
        adapter = FirebaseCrudAdapter()
        self.gaia = GaiaEngine(adapter)
        self.binder = MedicalBinder(adapter, self.gaia)

    def set_current_user(self, google_id: str):
        self.binder.current_user = google_id

    def get_finance_stats(self, start=None, end=None):
        data = self.gaia.compute_finance(self.binder.current_user, start, end)
        return data

    def get_productivity_stats(self, start=None, end=None):
        return self.gaia.compute_productivity(self.binder.current_user, start, end)

    def get_roi_stats(self, start=None, end=None):
        return self.gaia.compute_roi(self.binder.current_user, start, end)
