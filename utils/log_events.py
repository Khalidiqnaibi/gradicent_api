from firebase_admin import db
from datetime import datetime

def log_event(google_id, event_type, metadata=None):
    """Save user activity for business analytics"""
    ref = db.reference('/analytics')
    event = {
        "user": google_id,
        "type": event_type,
        "meta": metadata or {},
        "timestamp": datetime.now().isoformat()
    }
    ref.push(event)