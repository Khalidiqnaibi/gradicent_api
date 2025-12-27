"""
avg_transaction_value_metric.py
-------------------------------
Average transaction value in date window. Prefer payment events (204,207), fallback to transactions.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
PAYMENT_EVENTS = [600,601,602,604]


class AvgTransactionValueMetric(IMetric):
    @property
    def name(self) -> str:
        return "avg_transaction_value"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        total = 0.0
        count = 0

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") in PAYMENT_EVENTS:
                    m = ev.get("meta") or {}
                    amt = float(m.get("amount", m.get("payed", 0) or 0) or 0)
                    if amt > 0:
                        total += amt
                        count += 1

        if count > 0:
            return {"avg_transaction_value": round(total / count, 2), "count": count, "source": "events"}

        # fallback: iterate client transactions but limited to those with timestamp in window
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        for c in clients:
            for t in c.get("transactions", []) or []:
                ts = t.get("timestamp")
                if ts:
                    t_parsed = parse_date(ts)
                    if not t_parsed or t_parsed < start or t_parsed > end:
                        continue
                try:
                    amt = float(t.get("amount", 0) or 0)
                except Exception:
                    amt = 0.0
                if amt > 0:
                    total += amt
                    count += 1

        avg = round(total / max(count, 1), 2) if count else 0.0
        return {"avg_transaction_value": avg, "count": count, "source": "clients"}
    

MetricRegistry.register(AvgTransactionValueMetric)
