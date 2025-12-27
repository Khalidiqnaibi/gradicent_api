"""
customer_lifetime_days_metric.py
--------------------------------
Date-bounded average lifetime using first-purchase (206) and heartbeat (208) events if present.
Fallback to created_at + last interaction.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from statistics import mean
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
EVENT_FIRST_PURCHASE = 600
EVENT_HEARTBEAT = [402,202]


class CustomerLifetimeDaysMetric(IMetric):
    @property
    def name(self) -> str:
        return "customer_lifetime_days"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        first_purchase = {}
        last_activity = {}

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                et = ev.get("type")
                ts = ev.get("timestamp")
                if not ts:
                    continue
                parsed = parse_date(ts)
                if not parsed:
                    continue
                m = ev.get("meta") or {}
                cid = m.get("client_id") or m.get("id")
                if not cid:
                    continue
                if et == EVENT_FIRST_PURCHASE:
                    if cid not in first_purchase or parsed < first_purchase[cid]:
                        first_purchase[cid] = parsed
                if et in EVENT_HEARTBEAT:
                    if cid not in last_activity or parsed > last_activity[cid]:
                        last_activity[cid] = parsed

        lifetimes = []
        if first_purchase:
            # compute per client using last_activity or fallback to client interactions
            for cid, start_dt in first_purchase.items():
                end_dt = last_activity.get(cid)
                if not end_dt:
                    # fallback: try to find last interaction on client record (cheap per client)
                    clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
                    cobj = next((c for c in clients if str(c.get("id")) == str(cid)), None)
                    last_ts = None
                    if cobj:
                        for i in (cobj.get("interactions", []) or []):
                            ts = i.get("timestamp")
                            if ts:
                                p = parse_date(ts)
                                if p and (last_ts is None or p > last_ts):
                                    last_ts = p
                    end_dt = last_ts
                if end_dt and end_dt >= start_dt:
                    lifetimes.append((end_dt - start_dt).days)
            avg = round(mean(lifetimes), 2) if lifetimes else None
            return {"avg_customer_lifetime_days": avg, "sample_size": len(lifetimes), "source": "events"}

        # fallback full client scan (bounded)
        clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
        lifetimes = []
        for c in clients:
            created = parse_date(c.get("created_at")) if c.get("created_at") else None
            last = None
            for i in (c.get("interactions", []) or []):
                ts = i.get("timestamp")
                if ts:
                    p = parse_date(ts)
                    if p and (last is None or p > last):
                        last = p
            if created and last and last >= created:
                lifetimes.append((last - created).days)
        avg = round(mean(lifetimes), 2) if lifetimes else None
        return {"avg_customer_lifetime_days": avg, "sample_size": len(lifetimes), "source": "clients"}


MetricRegistry.register(CustomerLifetimeDaysMetric)
