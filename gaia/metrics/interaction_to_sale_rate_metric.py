"""
interaction_to_sale_rate_metric.py
----------------------------------
How many interactions inside date window result in payments.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30


class InteractionToSaleRateMetric(IMetric):
    @property
    def name(self) -> str:
        return "interaction_to_sale_rate"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        interactions = 0
        paid = 0

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") == 202:
                    interactions += 1
                    payed = float((ev.get("meta") or {}).get("payed", 0) or 0)
                    if payed > 0:
                        paid += 1

        rate = round((paid / max(interactions, 1)) * 100, 2)
        return {"interaction_count": interactions, "paid_interactions": paid, "conversion_percent": rate, "source": "events"}


MetricRegistry.register(InteractionToSaleRateMetric)
