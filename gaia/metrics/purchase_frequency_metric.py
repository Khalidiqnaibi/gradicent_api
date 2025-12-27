"""
purchase_frequency_metric.py
----------------------------
Date-bounded average purchases per paying customer.
Uses payment events first, fallback to transactions.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
PAYMENT_EVENTS = [600,601,602,604]


class PurchaseFrequencyMetric(IMetric):
    @property
    def name(self) -> str:
        return "purchase_frequency"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        counts = defaultdict(int)
        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") in PAYMENT_EVENTS:
                    m = ev.get("meta") or {}
                    cid = m.get("client_id") or m.get("id")
                    amt = float(m.get("amount", m.get("payed", 0) or 0) or 0)
                    if cid and amt:
                        counts[str(cid)] += 1

        if counts:
            avg = round(sum(counts.values()) / len(counts), 2)
            return {"avg_purchases_per_customer": avg, "customers_counted": len(counts), "source": "events"}

        # fallback to transactions
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        counts = defaultdict(int)
        for c in clients:
            for t in (c.get("transactions", []) or []):
                ts = t.get("timestamp")
                if ts:
                    t_parsed = parse_date(ts)
                    if not t_parsed or t_parsed < start or t_parsed > end:
                        continue
                amt = float(t.get("amount", 0) or 0)
                if amt:
                    counts[str(c.get("id"))] += 1

        if counts:
            avg = round(sum(counts.values()) / len(counts), 2)
            return {"avg_purchases_per_customer": avg, "customers_counted": len(counts), "source": "clients"}

        return {"avg_purchases_per_customer": 0.0, "customers_counted": 0, "source": "none"}


MetricRegistry.register(PurchaseFrequencyMetric)
