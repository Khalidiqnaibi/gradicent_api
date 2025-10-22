from typing import Any, Dict, List

from ..adapter import DomainAdapter
from firebase_admin import db

class FirebaseAdapter(DomainAdapter):
    """
    Minimal Firebase adapter for your existing structure. Assumes firebase_admin initialized.
    """

    def __init__(self, root: str = "/"):
        self.root = root

    def _safe_values(self, obj: Any) -> List[Dict[str, Any]]:
        if not obj:
            return []
        if isinstance(obj, dict):
            return [v for k, v in obj.items()]
        if isinstance(obj, list):
            return obj
        return []

    def fetch_time_logs(self, user_id: str) -> List[Dict[str, Any]]:
        all_logs = db.reference('/time_tracking').get() or {}
        return [v for k, v in (all_logs.items() if isinstance(all_logs, dict) else []) if v.get("user") == user_id]

    def fetch_analytics(self, user_id: str) -> List[Dict[str, Any]]:
        all_analytics = db.reference('/analytics').get() or {}
        return [v for k, v in (all_analytics.items() if isinstance(all_analytics, dict) else []) if v.get("user") == user_id]

    def fetch_user_doc(self, user_id: str) -> Dict[str, Any]:
        return db.reference(f'/drs/{user_id}').get() or {}

    def fetch_entities(self, user_id: str) -> List[Dict[str, Any]]:
        doc = self.fetch_user_doc(user_id)
        return doc.get('patients', []) if isinstance(doc.get('patients', []), list) else []
