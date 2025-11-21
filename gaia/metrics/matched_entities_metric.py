"""
matched_entities_metric.py
--------------------------
Return full matched entity objects for the active domain.

Why:
- Acts as the core dataset provider for analytics dashboards.
- Keeps data immutable by returning deep copies only.
"""

from typing import Dict, Any, List
import copy
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import filter_patients, filter_clients, DOMAIN_ENTITY_MAP

logger = logging.getLogger(__name__)


class MatchedEntitiesMetric(IMetric):
    """Return matched entities as deep-copied objects."""

    @property
    def name(self) -> str:
        return "matched_entities"

    def compute(self, binder, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """
        Compute matched entities.

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
            dict: {"entities": list}
        """
        domain = kwargs.get("domain", "medical")
        entity_key = DOMAIN_ENTITY_MAP.get(domain, "patients")

        raw_entities = binder.adapter.list_children(
            binder.current_user, entity_key
        ) or {}
        entities = list(raw_entities.values())

        if domain == "medical":
            matched = filter_patients(entities, kwargs)

        elif domain == "business":
            matched = filter_clients(entities, kwargs)

        else:
            matched = []

        result = copy.deepcopy(matched)

        logger.debug(
            "matched_entities calculated domain=%s count=%d",
            domain,
            len(result),
        )

        return {"entities": result}


MetricRegistry.register(MatchedEntitiesMetric)
