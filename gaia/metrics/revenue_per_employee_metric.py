"""
revenue_per_employee_metric.py
------------------------------
Revenue per employee inside the date window.
Uses metadata.finance if present, fallback to aggregating payments by assignee.
"""

from typing import Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30
PAYMENT_EVENTS = [600,601,602,604]


class RevenuePerEmployeeMetric(IMetric):
    @property
    def name(self) -> str:
        return "revenue_per_employee"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        # quick path: metadata.finance.total_revenue if already computed and bounded
        finance = meta.get("finance", {}) or {}
        total_revenue = float(finance.get("total_revenue", 0) or 0)
        employees = binder.adapter.list_children(binder.domain, binder.current_user, "employees") or []
        if total_revenue and employees:
            per = round(total_revenue / max(len(employees), 1), 2)
            return {"revenue_per_employee": per, "employee_count": len(employees), "total_revenue": total_revenue, "source": "metadata"}

        # fallback: aggregate payments by assignee in events
        analytics = meta.get("analytics", {}) or {}
        agg = defaultdict(float)
        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                if ev.get("type") in PAYMENT_EVENTS:
                    m = ev.get("meta") or {}
                    amt = float(m.get("amount", m.get("payed", 0) or 0) or 0)
                    ass = m.get("assignee") or m.get("employee_id")
                    if ass and amt:
                        agg[str(ass)] += amt

        total = sum(agg.values())
        count = len(agg) or len(employees) or 0
        per = round(total / max(count, 1), 2) if count else 0.0
        return {"revenue_per_employee": per, "employee_count": count, "total_revenue": total, "source": "events_or_clients"}


MetricRegistry.register(RevenuePerEmployeeMetric)
