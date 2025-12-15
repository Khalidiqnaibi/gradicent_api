"""
total_customers_metric.py
-------------------------
Compute the number of patients matching the provided filters.

Why:
- Small, single-responsibility metric for counting matched patients.
"""

from typing import Dict, Any
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import filter_patients , DOMAIN_ENTITY_MAP,filter_clients
from binder import normalize_user

logger = logging.getLogger(__name__)


class TotalCustomersMetric(IMetric):
    """Return the count of patients matching provided filters."""

    @property
    def name(self) -> str:
        return "total_customers"

    def compute(self, binder, **kwargs) -> Dict[str, int]:
        """
        Compute matched patient count.

        Args:
            binder: Gaia binder with adapter and current_user.

            **kwargs (filter options):
                Common:
                    user_id (str) : binders user id in the db
                    domain (str): "medical" | "business" | "education" | optional
                    start_date | From (str): "YYYY-MM-DD"
                    end_date | To   (str): "YYYY-MM-DD"
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
            dict: {"total_customers": int}
        """
        domain = kwargs.get("domain", "medical").lower()

        # Which collection do we load?
        entity_collection = DOMAIN_ENTITY_MAP.get(domain, "clients")

        # ----------------------
        # Switch binder user (if client called with ?user_id=)
        # ----------------------
        userid = kwargs.get("user_id")
        if userid:
            binder.adapter.current_user = userid

        # ----------------------
        # FAST LOAD — only the clients/patients/customers array
        # ----------------------
        entities = binder.adapter.list_children(
            binder.current_user,
            entity_collection
        ) or binder.adapter.list_children(
            binder.current_user,
            "clients"
        ) or []

        # ----------------------
        # Apply correct filter per domain
        # ----------------------
        if domain == "medical":
            matched = filter_patients(list(entities), kwargs)
        else:  # business, sales, etc.
            matched = filter_clients(list(entities), kwargs)

        # ----------------------
        # Return count
        # ----------------------
        return {"total_customers": len(matched)}


MetricRegistry.register(TotalCustomersMetric)
