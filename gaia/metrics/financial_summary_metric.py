"""
financial_summary_metric.py
---------------------------
Aggregate total debit and paid amounts across matched entities.

Why:
- Provides a single source of truth for financial summaries.
- Keeps write-free, read-only metrics for analytics.
"""

from typing import Dict, Any
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import filter_patients, filter_clients, DOMAIN_ENTITY_MAP

logger = logging.getLogger(__name__)


class FinancialSummaryMetric(IMetric):
    """Compute total debit and paid values."""

    @property
    def name(self) -> str:
        return "financial_summary"

    def compute(self, binder, **kwargs) -> Dict[str, float]:
        """
        Compute financial totals.

        Args:
            binder: Gaia binder with adapter and current_user.

            **kwargs (filter options):
                Common:
                    domain (str): "medical" | "business"
                    start_date (str): "YYYY-MM-DD"
                    end_date (str): "YYYY-MM-DD"
                    details (str)
                    location (str)
                    show_date (bool)
                    show_visit_info (bool)

                Medical-only:
                    treatment (str)
                    diagnosis (str)
                    lab (str)

                Business-only:
                    product (str)
                    service (str)

        Returns:
            dict: {"total_debit": float, "total_payed": float}
        """
        domain = kwargs.get("domain", "medical")
        entity_key = DOMAIN_ENTITY_MAP.get(domain, "patients")

        raw_entities = binder.adapter.list_children(
           binder.domain,binder.current_user, entity_key
        ) or []
        entities = list(raw_entities)

        total_debit = 0.0
        total_payed = 0.0

        if domain == "medical":
            matched = filter_patients(entities, kwargs)

            for patient in matched:
                for visit in patient.get("visits", []) or []:
                    debit = float(visit.get("debit", 0) or 0)
                    payed = float(visit.get("payed", 0) or 0)

                    if "div" in visit:
                        debit *= 10
                        payed *= 10

                    total_debit += debit
                    total_payed += payed

        elif domain == "business":
            # feel like this logic doesnt make sense might have to change after testing with some bus binder users
            matched = filter_clients(entities, kwargs)

            for client in matched:
                for txn in client.get("transactions", []) or []:
                    amount = float(txn.get("amount", 0) or 0)
                    is_paid = txn.get("paid", False)

                    if is_paid:
                        total_payed += amount
                    else:
                        total_debit += amount

        logger.debug(
            "financial_summary calculated domain=%s debit=%s paid=%s",
            domain,
            total_debit,
            total_payed,
        )

        return {
            "total_debit": total_debit,
            "total_payed": total_payed,
        }


MetricRegistry.register(FinancialSummaryMetric)
