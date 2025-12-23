"""
financial_summary_metric.py
---------------------------
Aggregate total debit and paid amounts across matched entities using events.

Why:
- Event-driven aggregation avoids unnecessary iteration over all entities.
- Single source of truth for financial summaries.
- Read-only metric suitable for analytics dashboards.
"""

from typing import Dict, Any, Set
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import DOMAIN_ENTITY_MAP, parse_date

logger = logging.getLogger(__name__)

# Event types relevant for finance
FINANCE_EVENTS = {
    202,  # interaction added
    402,  # interaction updated
    401,
}


class FinancialSummaryMetric(IMetric):
    """Compute total debit and paid values efficiently."""

    @property
    def name(self) -> str:
        return "financial_summary"

    def compute(self, binder, **kwargs) -> Dict[str, float]:
        domain = kwargs.get("domain", binder.domain)
        entity_key = DOMAIN_ENTITY_MAP.get(domain, "patients")

        # -------------------------
        # Date range
        # -------------------------
        start = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end   = parse_date(kwargs.get("end_date")   or kwargs.get("to")   or kwargs.get("To"))

        # -------------------------
        # Load analytics once
        # -------------------------
        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {})

        total_debit = 0.0
        total_payed = 0.0

        for day, payload in analytics.items():
            day_dt = parse_date(day)
            if (start and day_dt and day_dt < start) or (end and day_dt and day_dt > end):
                continue

            for ev in payload.get("events", []):
                etype = ev.get("type")
                if etype not in FINANCE_EVENTS:
                    continue

                meta_data = ev.get("meta") or {}

                # ---- medical domain ----
                if domain == "medical":
                    payed = float(meta_data.get("payed", 0) or 0)
                    debit = float(meta_data.get("debit", 0) or 0)

                    # handle legacy 'div' factor
                    if "div" in meta_data:
                        payed *= 10
                        debit *= 10

                    total_payed += payed
                    total_debit += debit

                # ---- business domain ----
                elif domain == "business":
                    amount = float(meta_data.get("amount", 0) or 0)
                    is_paid = meta_data.get("paid", False)

                    if is_paid:
                        total_payed += amount
                    else:
                        total_debit += amount

        logger.debug(
            "financial_summary domain=%s debit=%.2f paid=%.2f",
            domain,
            total_debit,
            total_payed,
        )

        return {
            "total_debit": round(total_debit, 2),
            "total_payed": round(total_payed, 2),
        }


MetricRegistry.register(FinancialSummaryMetric)
