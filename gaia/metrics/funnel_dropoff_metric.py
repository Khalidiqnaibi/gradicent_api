"""
funnel_dropoff_metric.py
------------------------
Estimate dropoff percentages for a date window:
  clients_added (201) -> interactions (202) -> paid interactions (204/207)
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
PAYMENT_EVENTS = [600,601,602,604]


class FunnelDropoffMetric(IMetric):
    @property
    def name(self) -> str:
        return "funnel_dropoff"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        clients_added = 0
        interactions = 0
        payments = 0

        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                et = ev.get("type")
                if et == 201:
                    clients_added += 1
                elif et == 202:
                    interactions += 1
                    m = ev.get("meta") or {}
                    if float(m.get("payed", 0) or m.get("amount", 0) or 0) > 0:
                        payments += 1
                elif et in PAYMENT_EVENTS:
                    # direct payment events count too
                    m = ev.get("meta") or {}
                    if float(m.get("amount", 0) or m.get("payed", 0) or 0) > 0:
                        payments += 1

        clients_to_interactions = round((interactions / max(clients_added, 1)) * 100, 2)
        interactions_to_payments = round((payments / max(interactions, 1)) * 100, 2)

        return {
            "clients_added": clients_added,
            "interactions": interactions,
            "payments": payments,
            "clients_to_interactions_pct": clients_to_interactions,
            "interactions_to_payments_pct": interactions_to_payments,
            "source": "events"
        }


MetricRegistry.register(FunnelDropoffMetric)
