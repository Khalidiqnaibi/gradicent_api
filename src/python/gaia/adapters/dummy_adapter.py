from typing import Any, Dict, List

from ..adapter import DomainAdapter

class DummyAdapter(DomainAdapter):
    """
    Simple in-memory adapter useful for quick testing and unit tests.
    """

    def __init__(self, data: Dict[str, Any]):
        # data is a dict keyed by user_id -> {time_logs, analytics, user_doc}
        self.data = data

    def fetch_time_logs(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.data.get(user_id, {}).get("time_logs", []))

    def fetch_analytics(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.data.get(user_id, {}).get("analytics", []))

    def fetch_user_doc(self, user_id: str) -> Dict[str, Any]:
        return dict(self.data.get(user_id, {}).get("user_doc", {}))

    def fetch_entities(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.data.get(user_id, {}).get("entities", []))
