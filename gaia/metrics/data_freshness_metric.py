"""
data_freshness_metric.py
------------------------
Return days since latest event in the date window (or overall latest if window omitted).
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30


class DataFreshnessMetric(IMetric):
    @property
    def name(self) -> str:
        return "data_freshness"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        latest = None

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                ts = ev.get("timestamp")
                if not ts:
                    continue
                parsed = parse_date(ts)
                if parsed and (latest is None or parsed > latest):
                    latest = parsed

        if latest is None:
            return {"days_since_last_event": None, "has_events": False}
        diff = (datetime.now(tz=latest.tzinfo) - latest).days
        return {"days_since_last_event": diff, "has_events": True}


MetricRegistry.register(DataFreshnessMetric)
