"""
productivity_metric.py
----------------------
Compute productivity metrics for a binder user using analytics events/time_tracking.

Outputs:
- total_time_minutes
- avg_time_per_session_minutes
- percent_productive (8–18h)
- visits_per_active_hour
- time_vs_patients (labels, minutes, patients)
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date, _in_range_dt

logger = logging.getLogger(__name__)

# Event type constants
EVENT_CLIENT_ADDED = 201
EVENT_INTERACTION_ADDED = 202

def _in_range_dt_inclusive(ts: datetime, start: datetime = None, end: datetime = None) -> bool:
    """
    Return True if ts is in [start, end] inclusive.
    Only compares date portion if start or end is date-only.
    """
    if not ts:
        return False
    t_date = ts.date()
    if start and t_date < start.date():
        return False
    if end and t_date > end.date():
        return False
    return True

def _parse_ts(value: str):
    """Parse ISO timestamp (with optional Z) into datetime or return None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

class ProductivityMetric(IMetric):
    @property
    def name(self):
        return "productivity"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        start_dt = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end_dt   = parse_date(kwargs.get("end_date") or kwargs.get("to") or kwargs.get("To"))

        userid = kwargs.get("user_id")
        if userid:
            binder.current_user = userid

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        total_seconds = 0.0
        productive_seconds = 0.0
        session_dates = set()
        visits = 0
        by_day: Dict[str, Dict[str, float]] = {}
        now = datetime.now()

        for day_str, payload in analytics.items():
            day_dt = parse_date(day_str)
            if day_dt and not _in_range_dt_inclusive(day_dt, start_dt, end_dt):
                continue

            # time_tracking
            for t in payload.get("time_tracking", []) or []:
                ts = _parse_ts(t.get("timestamp"))
                if not ts or not _in_range_dt_inclusive(ts, start_dt, end_dt):
                    continue

                seconds = float(t.get("seconds", 0) or 0)
                total_seconds += seconds
                if 8 <= ts.hour < 18:
                    productive_seconds += seconds

                key = ts.date().isoformat()
                bucket = by_day.setdefault(key, {"minutes": 0.0, "patients": 0})
                bucket["minutes"] += seconds / 60.0
                session_dates.add(ts.date().isoformat())

            # events
            for ev in payload.get("events", []) or []:
                ts = _parse_ts(ev.get("timestamp"))
                if not ts or not _in_range_dt_inclusive(ts, start_dt, end_dt):
                    continue

                etype = ev.get("type")
                if etype == EVENT_INTERACTION_ADDED:
                    visits += 1
                if etype == EVENT_CLIENT_ADDED:
                    key = ts.date().isoformat()
                    bucket = by_day.setdefault(key, {"minutes": 0.0, "patients": 0})
                    bucket["patients"] += 1

        total_minutes = round(total_seconds / 60.0, 2)
        session_count = max(1, len(session_dates))
        avg_per_session = round(total_minutes / session_count, 2)
        percent_productive = round((productive_seconds / (total_seconds or 1)) * 100, 1)
        active_hours = max(0.01, total_seconds / 3600.0)
        visits_per_active_hour = round(visits / active_hours, 2)

        labels = sorted(by_day.keys())
        minutes = [round(by_day[d]["minutes"], 2) for d in labels]
        patients = [int(by_day[d]["patients"]) for d in labels]

        result = {
            "total_time_minutes": total_minutes,
            "avg_time_per_session_minutes": avg_per_session,
            "percent_productive": percent_productive,
            "visits_per_active_hour": visits_per_active_hour,
            "time_vs_patients": {
                "labels": labels,
                "minutes": minutes,
                "patients": patients,
            },
        }

        logger.debug("productivity computed user=%s start=%s end=%s result=%s",
                     binder.current_user, start_dt, end_dt, result)

        return result

MetricRegistry.register(ProductivityMetric)
