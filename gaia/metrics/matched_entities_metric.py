"""
matched_entities_metric.py
--------------------------
Return matched entity objects for the active domain,
using analytics events as the primary index.
"""

from typing import Dict, Any, Set
import logging

from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import (
    DOMAIN_ENTITY_MAP,
    parse_date,
    filter_entities_with_events,
)

logger = logging.getLogger(__name__)


class MatchedEntitiesMetric(IMetric):
    """
    Core dataset provider for analytics dashboards.

    Characteristics:
    - Event-driven (O(events + matched visits))
    - No entity mutation
    - No deep copies
    - Deterministic and fast
    """

    @property
    def name(self) -> str:
        return "matched_entities"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        domain = kwargs.get("domain", binder.domain)
        entity_key = DOMAIN_ENTITY_MAP.get(domain, "patients")

        # Date range
        start = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end   = parse_date(kwargs.get("end_date")   or kwargs.get("to")   or kwargs.get("To"))

        # Load analytics ONCE
        meta = binder.adapter.get_child(
            binder.domain, binder.current_user, "metadata"
        ) or {}

        analytics = meta.get("analytics", {})

        # Classify entity activity from events
        new_ids: Set[str] = set()
        returning_ids: Set[str] = set()

        for day, payload in analytics.items():
            day_dt = parse_date(day)
            if (start and day_dt and day_dt < start) or (end and day_dt and day_dt > end):
                continue

            for ev in payload.get("events", []):
                etype = ev.get("type")
                meta  = ev.get("meta") or {}

                eid = (
                    meta.get("entity_id")
                    or meta.get("patient")
                    or meta.get("client")
                    or meta.get("id")
                )

                if not eid:
                    continue

                eid = str(eid)

                # creation
                if etype == 201:
                    new_ids.add(eid)

                # interaction/update
                elif etype == 202:
                    returning_ids.add(eid)

        touched_ids = new_ids | returning_ids
        if not touched_ids:
            return {
                "entities": [],
                "new": [],
                "returning": [],
            }

        # Load entities ONCE
        entities = (
            binder.adapter.list_children(
                binder.domain, binder.current_user, entity_key
            )
            or []
        )

        # Filter entities (events + visits)
        matched = filter_entities_with_events(
            entities,
            analytics=analytics,
            filters=kwargs,
            entity_id_key="id",
            date_key="visit_date" if domain == "medical" else "interaction_date",
        )

        # Classify matched entities
        matched_new = []
        matched_returning = []

        for ent in matched:
            eid = str(ent.get("id"))

            if eid in new_ids:
                matched_new.append(ent)
            elif eid in returning_ids:
                matched_returning.append(ent)

        logger.debug(
            "matched_entities domain=%s total=%d new=%d returning=%d",
            domain,
            len(matched),
            len(matched_new),
            len(matched_returning),
        )

        return {
            "entities": matched,
            "new": matched_new,
            "returning": matched_returning,
        }


MetricRegistry.register(MatchedEntitiesMetric)
