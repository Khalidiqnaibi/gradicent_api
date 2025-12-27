"""
revenue_per_product_metric.py
-----------------------------
Aggregate revenue per product inside date window using product_purchase (207) events.
"""

from typing import Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
EVENT_PRODUCT_PURCHASE = 602


class RevenuePerProductMetric(IMetric):
    @property
    def name(self) -> str:
        return "revenue_per_product"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        agg = defaultdict(float)
        found = False

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") == EVENT_PRODUCT_PURCHASE:
                    m = ev.get("meta") or {}
                    pid = m.get("product_id")
                    amt = float(m.get("amount", m.get("payed", 0) or 0) or 0)
                    if pid and amt:
                        agg[str(pid)] += amt
                        found = True

        if found:
            return {"revenue_per_product": dict(agg), "source": "events"}

        # fallback: per-client transactions inside window
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        for c in clients:
            for t in c.get("transactions", []) or []:
                ts = t.get("timestamp")
                if ts:
                    t_parsed = parse_date(ts)
                    if not t_parsed or t_parsed < start or t_parsed > end:
                        continue
                m = t.get("metadata") or {}
                pid = m.get("product_id")
                try:
                    amt = float(t.get("amount", 0) or 0)
                except Exception:
                    amt = 0.0
                if pid and amt:
                    agg[str(pid)] += amt

        return {"revenue_per_product": dict(agg), "source": "clients"}
    

MetricRegistry.register(RevenuePerProductMetric)
