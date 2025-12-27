"""
ltv_metric.py
--------------
Date-bounded LTV estimate using payment events if available.
Simple, robust proxy: avg_transaction_value * avg_purchases_per_customer
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
PAYMENT_EVENTS = {204, 207}


class LTVMetric(IMetric):
    @property
    def name(self) -> str:
        return "ltv"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        total_paid = 0.0
        purchases_per_customer = defaultdict(int)

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") in PAYMENT_EVENTS:
                    m = ev.get("meta") or {}
                    amt = float(m.get("amount", m.get("payed", 0) or 0) or 0)
                    cid = m.get("client_id") or m.get("id")
                    if amt and cid:
                        total_paid += amt
                        purchases_per_customer[str(cid)] += 1

        if purchases_per_customer:
            avg_tx = round(total_paid / sum(purchases_per_customer.values()), 2)
            avg_purchases = round(sum(purchases_per_customer.values()) / len(purchases_per_customer), 2)
            ltv = round(avg_tx * avg_purchases, 2)
            return {
                "ltv": ltv,
                "avg_transaction_value": avg_tx,
                "avg_purchases_per_customer": avg_purchases,
                "customers_counted": len(purchases_per_customer),
                "source": "events"
            }

        # fallback: compute from client records (bounded)
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        total = 0.0
        counts = defaultdict(int)
        for c in clients:
            for t in (c.get("transactions", []) or []):
                try:
                    amt = float(t.get("amount", 0) or 0)
                except Exception:
                    amt = 0.0
                if amt:
                    total += amt
                    counts[str(c.get("id"))] += 1
        if counts:
            avg_tx = round(total / sum(counts.values()), 2)
            avg_purchases = round(sum(counts.values()) / len(counts), 2)
            ltv = round(avg_tx * avg_purchases, 2)
            return {"ltv": ltv, "avg_transaction_value": avg_tx, "avg_purchases_per_customer": avg_purchases, "customers_counted": len(counts), "source": "clients"}

        return {"ltv": 0.0, "avg_transaction_value": 0.0, "avg_purchases_per_customer": 0.0, "customers_counted": 0, "source": "none"}


MetricRegistry.register(LTVMetric)
