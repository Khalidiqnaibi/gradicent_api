from datetime import datetime
from typing import Any, Optional

def parse_date_or_timestamp(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    """
    Robust parsing: accepts int/float timestamps, ISO strings (with Z), and microsecond ISO.
    Returns None (or provided default) when parsing fails.
    """
    if value is None or value == "":
        return default
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        if isinstance(value, str):
            try:
                # handle Zulu timezone by substituting +00:00
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                # fallback to common microsecond format
                try:
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
                except Exception:
                    return default
    except Exception:
        return default

def in_range_dt(dt: Optional[datetime], start_dt: Optional[datetime], end_dt: Optional[datetime]) -> bool:
    if dt is None:
        return False
    return (start_dt is None or dt >= start_dt) and (end_dt is None or dt <= end_dt)

def matches_entity_filter(entity_filter: Any, obj: Any) -> bool:
    """
    Generic entity matching (patients/customers). Compares common keys or direct string equality.
    """
    if not entity_filter:
        return True
    if obj is None:
        return False
    if isinstance(obj, dict):
        for k in ("id", "entity_id", "patient", "patient_id", "name"):
            v = obj.get(k)
            if v is None:
                continue
            if str(v) == str(entity_filter):
                return True
    if isinstance(obj, str) and obj == str(entity_filter):
        return True
    return False
