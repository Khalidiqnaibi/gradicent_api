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
            **kwargs: filter options (startDate / start_date, endDate, details, etc.)
            for medical: 
                kwargs = {
                    "domain" = "medical" or None,"start_date","end_date","details"
                    "location","treatment","diagnosis",
                    "lab","show_date","show_visit_info"
                }

            for business: 
                kwargs = {
                    "domain" = "business" (not optional),"start_date","end_date","details"
                    "location","product","service",
                    "show_date","show_visit_info"
                }

        Returns:
            dict: {"total_customers": int}
        """
        # collect patients and normalize to a list
        DOMAIN = kwargs.get("domain","medical")
        if DOMAIN in ["medical"]:
            raw_clients= binder.adapter.list_children(binder.current_user, DOMAIN_ENTITY_MAP[DOMAIN]) or {}
            clients = list(raw_clients.values())
            matched = filter_patients(clients, kwargs)
            total = len(matched)
        elif DOMAIN in ["business"]:
            raw_clients= binder.adapter.list_children(binder.current_user, DOMAIN_ENTITY_MAP[DOMAIN]) or {}
            clients = list(raw_clients.values())
            matched = filter_clients(clients, kwargs)
            total = len(matched)
        

        logger.debug("total_customers computed: %d", total)
        return {"total_customers": total}


MetricRegistry.register(TotalCustomersMetric)
