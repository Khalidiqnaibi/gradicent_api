"""
lead_source_distribution_metric.py
---------------------------------
Aggregate lead.source from client-added events in the date window.
"""

from typing import Dict, Any
from collections import Counter
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30


class LeadSourceDistributionMetric(IMetric):
    @property
    def name(self) -> str:
        return "lead_source_distribution"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        counter = Counter()
        total = 0

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") == 201:
                    src = (ev.get("meta") or {}).get("source") or "unknown"
                    counter[src] += 1
                    total += 1

        return {"distribution": dict(counter), "total_leads": total, "source": "events"}


MetricRegistry.register(LeadSourceDistributionMetric)
