from typing import Optional, Dict
from config import EVENTS

def log_event(binder, event_code: int, entity_id: Optional[str] = None, metadata: Optional[Dict] = None):
    """
    The primary logging function. 
    Usage: log_event(binder_service, 201, entity_id="client_abc", metadata={"source": "mobile"})
    """
    event_name = EVENTS.get(event_code, "unknown event")
    
    try:
        binder.adapter.log_event(
            domain=binder.domain,
            user_id=binder.current_user,
            event_code=event_code,
            event_name=event_name,
            entity_id=entity_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"Logging failed: {e}")

def log_time_spent(binder, seconds: int, activity_type: str = "usage"):
    """Specific helper for time tracking using the events table."""
    log_event(binder, 700, metadata={"seconds": seconds, "type": activity_type})