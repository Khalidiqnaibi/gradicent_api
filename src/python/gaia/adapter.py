from typing import Any, Dict, List, Protocol

class DomainAdapter(Protocol):
    """
    Protocol that adapters must implement. Adapters isolate datastore specifics
    and return normalized lists/dicts Gaia expects.
    """

    def fetch_time_logs(self, user_id: str) -> List[Dict[str, Any]]:
        ...

    def fetch_analytics(self, user_id: str) -> List[Dict[str, Any]]:
        ...

    def fetch_user_doc(self, user_id: str) -> Dict[str, Any]:
        ...

    def fetch_entities(self, user_id: str) -> List[Dict[str, Any]]:
        ...
