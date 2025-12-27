"""
manual_work_ratio_metric.py
---------------------------
Percent of manual events (updates, file uploads) inside date window.
Useful for operational overload signals.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
MANUAL_TYPES = {400, 401, 402, 203,204,205,206,403,404,405,406}


class ManualWorkRatioMetric(IMetric):
    @property
    def name(self) -> str:
        return "manual_work_ratio"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        total = 0
        manual = 0

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                total += 1
                if ev.get("type") in MANUAL_TYPES:
                    manual += 1

        ratio = round((manual / max(total, 1)) * 100, 2) if total else 0.0
        return {"manual_events": manual, "total_events": total, "manual_ratio_percent": ratio, "source": "events"}


MetricRegistry.register(ManualWorkRatioMetric)
