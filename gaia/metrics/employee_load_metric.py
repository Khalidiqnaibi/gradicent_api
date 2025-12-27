"""
employee_load_metric.py
-----------------------
Estimate employee workload inside a date window.
Prefers explicit employee metadata; fallback to counting assigned interactions events.
"""

from typing import Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30


class EmployeeLoadMetric(IMetric):
    @property
    def name(self) -> str:
        return "employee_load"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        employees = binder.adapter.list_children(binder.domain, binder.current_user, "employees") or []
        loads = {}
        # prefer explicit metadata hours
        for e in employees:
            hours = float(e.get("metadata", {}).get("hours_per_week", 0) or 0)
            loads[str(e.get("id"))] = hours

        if loads:
            avg = round(sum(loads.values()) / max(len(loads), 1), 2)
            return {"employee_loads": loads, "avg_load": avg, "count": len(loads), "source": "employees"}

        # fallback: compute counts of events assigned to employee in window
        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}
        counts = defaultdict(int)
        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                assignee = (ev.get("meta") or {}).get("assignee")
                if assignee:
                    counts[str(assignee)] += 1

        avg = round(sum(counts.values()) / max(len(counts), 1), 2) if counts else 0.0
        return {"employee_loads": dict(counts), "avg_load": avg, "count": len(counts), "source": "events"}


MetricRegistry.register(EmployeeLoadMetric)
