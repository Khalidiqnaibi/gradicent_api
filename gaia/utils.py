"""
utils.py
--------
High-performance filtering utilities.

Design principles:
- Events are the primary index (fast path)
- Visits are the verification step (slow path)
- No mutation of entities or visits
- No preprocessing unless required
"""

from datetime import datetime
from typing import Optional, List, Dict, Set

# -------------------------
# Domain mapping
# -------------------------

DOMAIN_ENTITY_MAP = {
    "medical": "patients",
    "business": "clients",
    "sales": "customers",
}

# -------------------------
# Event types that imply entity activity
# -------------------------

RELEVANT_VISIT_EVENTS = {
    201,  # client added
    202,  # interaction added
}

# -------------------------
# Date parsing
# -------------------------

def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO string into datetime (safe)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

# -------------------------
# Event-based candidate extraction
# -------------------------

def candidate_entities_from_events(
    analytics: Dict,
    *,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> Set[str]:
    """
    Extract entity IDs that appear in relevant events
    within the requested date range.
    """

    candidates: Set[str] = set()

    for day, payload in analytics.items():
        try:
            day_dt = datetime.fromisoformat(day)
        except Exception:
            continue

        if start_date and day_dt < start_date:
            continue
        if end_date and day_dt > end_date:
            continue

        for e in payload.get("events", []):
            if e.get("type") not in RELEVANT_VISIT_EVENTS:
                continue

            meta = e.get("meta") or {}
            entity_id = (
                meta.get("patient")
                or meta.get("client")
                or meta.get("entity_id")
            )

            if entity_id:
                candidates.add(entity_id)

    return candidates

# -------------------------
# Visit matcher (lean)
# -------------------------

def visit_matches(
    visit: Dict,
    *,
    details: str,
    filters: Dict[str, str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_key: str,
) -> bool:
    """Return True if a single visit matches all filters."""

    if details:
        v_details = (visit.get("details") or "").lower()
        if details not in v_details:
            return False

    for key, value in filters.items():
        if value and value not in (visit.get(key) or "").lower():
            return False

    if start_date or end_date:
        raw = visit.get(date_key)
        if not raw:
            return False

        try:
            vd = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return False

        if start_date and vd < start_date:
            return False
        if end_date and vd > end_date:
            return False

    return True

# -------------------------
# Unified entity filter
# -------------------------

def filter_entities_with_events(
    entities: List[Dict],
    *,
    analytics: Dict,
    filters: Dict,
    entity_id_key: str,
    date_key: str,
) -> List[Dict]:
    """
    Filter entities using:
    1) Event-based preselection (fast)
    2) Visit-level verification (accurate)
    """

    details = (filters.get("details") or "").lower()
    location = (filters.get("location") or "").lower()

    visit_filters = {
        k: (filters.get(k) or "").lower()
        for k in ("treatment", "diagnosis", "lab", "service", "product")
        if filters.get(k)
    }

    start_date = parse_date(filters.get("start_date") or filters.get("from"))
    end_date   = parse_date(filters.get("end_date")   or filters.get("to"))

    # -------- FAST PATH (events) --------

    candidate_ids = candidate_entities_from_events(
        analytics,
        start_date=start_date,
        end_date=end_date,
    )

    if not candidate_ids:
        return []

    # -------- SLOW PATH (visits) --------

    matched = []

    for entity in entities:
        eid = entity.get(entity_id_key)
        if eid not in candidate_ids:
            continue

        if location and location != (entity.get("location") or "").lower():
            continue

        visits = entity.get("interactions") or []
        if not isinstance(visits, list):
            visits = [visits]

        for v in visits:
            if visit_matches(
                v,
                details=details,
                filters=visit_filters,
                start_date=start_date,
                end_date=end_date,
                date_key=date_key,
            ):
                matched.append(entity)
                break

    return matched


def _in_range_dt(ts: datetime, start: datetime = None, end: datetime = None) -> bool:
    """
    Check if a datetime is within an optional start and end range (inclusive).

    Args:
        ts (datetime): The timestamp to check.
        start (datetime, optional): Start of the range. Defaults to None.
        end (datetime, optional): End of the range. Defaults to None.

    Returns:
        bool: True if ts is within range, False otherwise.
    """
    if not ts:
        return False
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True

