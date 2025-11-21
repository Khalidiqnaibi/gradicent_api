"""
unpaid_customers_metric.py
--------------------------
Count entities (patients or clients) that have unpaid financial balances.

Why:
- Provides a focused metric for outstanding debt monitoring.
- Works across multiple domains using domain-aware filtering.
"""

from typing import Dict, Any
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import filter_patients, filter_clients, DOMAIN_ENTITY_MAP

logger = logging.getLogger(__name__)


class UnpaidCustomersMetric(IMetric):
    """Count entities with unpaid debit based on filters."""

    @property
    def name(self) -> str:
        return "unpaid_customers"

    def compute(self, binder, **kwargs) -> Dict[str, int]:
        """
        Compute unpaid entity count.

        Args:
            binder: Gaia binder with adapter and current_user.

            **kwargs (filter options):
                Common:
                    domain (str): "medical" | "business" | "education" | optional
                    start_date (str): "YYYY-MM-DD"
                    end_date   (str): "YYYY-MM-DD"
                    details    (str): free text
                    location   (str): free text
                    show_date (bool): filter by date
                    show_visit_info (bool): enable visit/transaction filtering

                Medical-only:
                    treatment (str)
                    diagnosis (str)
                    lab (str)

                Business-only:
                    product (str)
                    service (str)

        Returns:
            dict: {"unpaid_customers": int}
        """
        domain = kwargs.get("domain", "medical")
        entity_key = DOMAIN_ENTITY_MAP.get(domain, "patients")

        raw_entities = binder.adapter.list_children(
            binder.current_user, entity_key
        ) or {}
        entities = list(raw_entities.values())

        total_unpaid = 0

        if domain == "medical":
            matched = filter_patients(entities, kwargs)

            for patient in matched:
                has_unpaid = False
                for visit in patient.get("visits", []) or []:
                    debit = float(visit.get("debit", 0) or 0)
                    if "div" in visit:
                        debit *= 10
                    if debit > 0:
                        has_unpaid = True
                        break

                if has_unpaid:
                    total_unpaid += 1

        elif domain == "business":
            matched = filter_clients(entities, kwargs)

            for client in matched:
                has_unpaid = False
                for txn in client.get("transactions", []) or []:
                    is_paid = txn.get("paid", False)
                    amount = float(txn.get("amount", 0) or 0)

                    if not is_paid and amount > 0:
                        has_unpaid = True
                        break

                if has_unpaid:
                    total_unpaid += 1

        logger.debug(
            "unpaid_customers calculated domain=%s count=%d",
            domain,
            total_unpaid,
        )

        return {"unpaid_customers": total_unpaid}


MetricRegistry.register(UnpaidCustomersMetric)
