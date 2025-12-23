"""
unpaid_customers_metric.py
--------------------------
Count entities (patients or clients) that have unpaid financial balances efficiently.

Strategy
--------
- If no visit/date/visit-field filters are provided, scan entities and count unpaid balances directly.
- Otherwise, use event-indexed filtering to preselect candidate entities before checking financials.
- Works for multiple domains and avoids unnecessary full scans.
"""

from typing import Dict, Any, List
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import (
    DOMAIN_ENTITY_MAP,
    parse_date,
    filter_entities_with_events,
)

logger = logging.getLogger(__name__)


class UnpaidCustomersMetric(IMetric):
    """Count entities (patients/clients) with unpaid balances."""

    @property
    def name(self) -> str:
        return "unpaid_customers"

    def compute(self, binder, **kwargs) -> Dict[str, int]:
        """
        Compute count of entities with unpaid financial balances.

        Common kwargs:
            domain (str): "medical" | "business" | "sales" (default: binder.domain)
            user_id (str): optional - operate on a different binder user
            start_date / From (str)
            end_date   / To   (str)
            details (str)
            location (str)
            (medical) treatment, diagnosis, lab
            (business) service, product

        Returns:
            {"unpaid_customers": int}
        """

        domain = (kwargs.get("domain") or binder.domain or "medical").lower()
        entity_collection = DOMAIN_ENTITY_MAP.get(domain, "patients")

        # Optional: temporarily switch the binder's current user
        userid = kwargs.get("user_id")
        if userid:
            try:
                binder.current_user = userid
            except Exception:
                try:
                    binder.adapter.current_user = userid
                except Exception:
                    logger.debug("Unable to set current_user to %s", userid, exc_info=True)

        # Load entity list
        entities: List[Dict] = binder.adapter.list_children(
            binder.domain, binder.current_user, entity_collection
        ) or []

        # ---------------------------
        # Detect trivial/no-op filters
        # ---------------------------
        start = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end = parse_date(kwargs.get("end_date") or kwargs.get("to") or kwargs.get("To"))
        details = (kwargs.get("details") or "").strip()
        location = (kwargs.get("location") or "").strip()

        if domain == "medical":
            visit_fields_present = any((kwargs.get(k) or "").strip() for k in ("treatment", "diagnosis", "lab"))
            date_filter_present = bool(start or end)
            trivial_filters = not (visit_fields_present or date_filter_present or details or location)
        else:
            visit_fields_present = any((kwargs.get(k) or "").strip() for k in ("service", "product"))
            date_filter_present = bool(start or end)
            trivial_filters = not (visit_fields_present or date_filter_present or details or location)

        # ---------------------------
        # Analytics load
        # ---------------------------
        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {})

        # ---------------------------
        # Event-prefiltering if non-trivial filters exist
        # ---------------------------
        if not trivial_filters:
            subset = filter_entities_with_events(
                entities,
                analytics=analytics,
                filters=kwargs,
                entity_id_key="id",
                date_key="visit_date" if domain == "medical" else "interaction_date",
            )
        else:
            subset = entities

        # ---------------------------
        # Count unpaid
        # ---------------------------
        total_unpaid = 0
        if domain == "medical":
            for patient in subset:
                for visit in patient.get("visits", []) or []:
                    debit = float(visit.get("debit", 0) or 0)
                    if "div" in visit:
                        debit *= 10
                    if debit > 0:
                        total_unpaid += 1
                        break  # one unpaid visit is enough
        else:
            for client in subset:
                for txn in client.get("transactions", []) or []:
                    is_paid = txn.get("paid", False)
                    amount = float(txn.get("amount", 0) or 0)
                    if not is_paid and amount > 0:
                        total_unpaid += 1
                        break  # one unpaid txn is enough

        logger.debug(
            "unpaid_customers domain=%s count=%d filters=%s",
            domain,
            total_unpaid,
            {k: v for k, v in kwargs.items() if k in ("start_date", "end_date", "details")},
        )

        return {"unpaid_customers": total_unpaid}


MetricRegistry.register(UnpaidCustomersMetric)
