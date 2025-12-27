"""
churn_rate_metric.py
--------------------
Date-bounded churn using heartbeat events (208) as cheap source.
Fallback to client interactions if no heartbeats in window.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
EVENT_HEARTBEAT = [402,202]


class ChurnRateMetric(IMetric):
    @property
    def name(self) -> str:
        return "churn_rate"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        inactive_days = int(kwargs.get("inactive_days", 30))
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))
        cutoff = datetime.now() - timedelta(days=inactive_days)

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        last_seen = {}
        found = False

        # gather heartbeat last-activity per client
        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") in EVENT_HEARTBEAT:
                    m = ev.get("meta") or {}
                    cid = m.get("client_id") or m.get("id")
                    ts = ev.get("timestamp")
                    if cid and ts:
                        p = parse_date(ts)
                        if p and (cid not in last_seen or p > last_seen[cid]):
                            last_seen[cid] = p
                            found = True

        if found:
            total = len(last_seen)
            churned = sum(1 for d in last_seen.values() if d < cutoff)
            rate = round((churned / max(total, 1)) * 100, 2)
            return {"churn_rate_percent": rate, "churned": churned, "total_customers": total, "source": "events"}

        # fallback: inspect clients' last interaction date (bounded)
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        total = len(clients)
        churned = 0
        for c in clients:
            # find latest interaction timestamp within client's interactions (full scan but bounded)
            last_ts = None
            for i in (c.get("interactions", []) or []):
                ts = i.get("timestamp")
                if ts:
                    p = parse_date(ts)
                    if p and (last_ts is None or p > last_ts):
                        last_ts = p
            if last_ts is None or last_ts < cutoff:
                churned += 1

        rate = round((churned / max(total, 1)) * 100, 2)
        return {"churn_rate_percent": rate, "churned": churned, "total_customers": total, "source": "clients"}


MetricRegistry.register(ChurnRateMetric)
