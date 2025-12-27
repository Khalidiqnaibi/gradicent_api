"""
tracking_coverage_metric.py
---------------------------
Date-bounded measure of how much of the product is tracked.
Uses events inside the date window and cheap user checks.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

DEFAULT_DAYS = 30


class TrackingCoverageMetric(IMetric):
    @property
    def name(self) -> str:
        return "tracking_coverage"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        """
        Returns:
            {
              "coverage_percent": float,
              "covered_sections": int,
              "total_sections": int,
              "source": "events"|"user"
            }
        """
        # date window
        end = parse_date(kwargs.get("to")) or datetime.now()
        start = parse_date(kwargs.get("from")) or (end - timedelta(days=DEFAULT_DAYS))

        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        has_clients = False
        has_interactions = False
        has_payments = False
        has_analytics_shown = False

        # iterate only days in window
        for day_key, day_payload in analytics.items():
            day_dt = parse_date(day_key)
            if not day_dt or day_dt < start or day_dt > end:
                continue
            for ev in day_payload.get("events", []) or []:
                et = ev.get("type")
                if et == 201:
                    has_clients = True
                elif et == 202:
                    has_interactions = True
                elif et == 204 or et == 207:  # payment/product purchase
                    has_payments = True
                elif et == 301:
                    has_analytics_shown = True
                if has_clients and has_interactions and has_payments and has_analytics_shown:
                    break
            if has_clients and has_interactions and has_payments and has_analytics_shown:
                break

        # cheap user checks
        user = binder.adapter.get(binder.domain, binder.current_user) or {}
        has_products = bool(user.get("products"))
        has_services = bool(user.get("services"))

        sections = [has_clients, has_interactions, has_payments, has_analytics_shown, has_products, has_services]
        covered = sum(1 for s in sections if s)
        total = len(sections)
        coverage = round((covered / max(total, 1)) * 100, 1)

        return {"coverage_percent": coverage, "covered_sections": covered, "total_sections": total, "source": "events_or_user"}


MetricRegistry.register(TrackingCoverageMetric)
