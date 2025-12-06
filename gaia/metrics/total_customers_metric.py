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
            dict: {"total_customers": int}
        """
        # collect patients and normalize to a list
        DOMAIN = kwargs.get("domain","medical")
        user = binder.adapter.get_user(binder.current_user)
        user = normalize_user(user).to_dict()

        if DOMAIN in ["medical"]:
            clients = user.get("clients")
            matched = filter_patients(clients, kwargs)
            total = len(matched)
        elif DOMAIN in ["business"]:
            clients = user.get("clients")
            matched = filter_clients(clients, kwargs)
            total = len(matched)
        else:# temp
            clients = user.get("clients")
            matched = filter_clients(clients, kwargs)
            total = len(matched)
        

        logger.debug("total_customers computed: %d", total)
        return {"total_customers": total}


MetricRegistry.register(TotalCustomersMetric)
