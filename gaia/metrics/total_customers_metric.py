"""
total_customers_metric.py
-------------------------
Event-driven counts for a time period + weekly series.

Returns:
- total_customers
- returning_customers
- avg_visits_per_customer
- weekly: { labels, counts (new unique per week), returning_counts (unique per week) }

Classification rule (updated):
- If an entity has a NEW event within the period -> it's NEW.
- It becomes RETURNING only if it has an interaction in the period **after** its NEW event's date.
- Interactions that occur on the same date as the NEW event do NOT count as returning.
- Entities created before the period with interactions in the period are RETURNING.
All timestamp comparisons are inclusive.
"""

from typing import Dict, Any, Set, DefaultDict, List
from collections import defaultdict
import logging
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

logger = logging.getLogger(__name__)

# Event codes (per your mapping)
EVENT_NEW = 201
EVENT_INTERACTION = 402


def _parse_iso_ts(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _in_range_inclusive(ts: datetime, start: datetime = None, end: datetime = None) -> bool:
    """
    Inclusive range check: True when start <= ts <= end.
    If start or end is None they are treated as unbounded.
    """
    if end:
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

    if not ts:
        return False
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True


def _extract_entity_id(ev_meta: dict):
    """Return canonical string id from event meta or None."""
    if not ev_meta:
        return None
    for k in ("entity_id", "patient", "client", "id"):
        v = ev_meta.get(k)
        if v is not None:
            return str(v)
    return None


def _monday_of(dt: datetime) -> datetime:
    """Return the date (datetime at 00:00) of the Monday of dt's week."""
    d = dt.date()
    monday = d - timedelta(days=d.weekday())  # weekday(): Monday=0
    return datetime(monday.year, monday.month, monday.day)


class TotalCustomersMetric(IMetric):
    @property
    def name(self) -> str:
        return "total_customers"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        # parse inclusive start/end
        start = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end = parse_date(kwargs.get("end_date") or kwargs.get("to") or kwargs.get("To"))
        
        if not start and not end:
            clients = binder.adapter.list_children(binder.domain, binder.current_user, "clients") or []
            return {
                "total_customers": len(clients),
                "returning_customers": 0,
                "avg_visits_per_customer": 0.0,
                "clients" : [],
                "weekly": {
                    "labels": [],
                    "counts": [],
                    "returning_counts": [],
                },
            }

        # load analytics (structure: analytics[day]['events'] = [...])
        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        # per-entity collectors (single pass)
        interaction_counts: DefaultDict[str, int] = defaultdict(int)
        first_new_ts: Dict[str, datetime] = {}         # earliest NEW event ts per eid (within period)
        first_interaction_ts: Dict[str, datetime] = {} # earliest interaction ts per eid (within period)
        seen_ids: Set[str] = set()                     # any entity seen in period by any event

        # weekly unique sets
        new_week_unique: DefaultDict[datetime, Set[str]] = defaultdict(set)
        interaction_week_unique: DefaultDict[datetime, Set[str]] = defaultdict(set)

        # track min/max timestamps for fallback ranges
        min_ts: datetime = None
        max_ts: datetime = None

        # Single pass over analytics -> days -> events
        for day_key, payload in analytics.items():
            day_dt = parse_date(day_key)

            # quick skip whole day if outside inclusive date range
            if day_dt:
                if start and day_dt.date() < start.date():
                    continue
                if end and day_dt.date() > end.date():
                    continue

            for ev in payload.get("events", []) or []:
                # event timestamp preferred
                ts = _parse_iso_ts(ev.get("timestamp"))
                if not ts:
                    ts = day_dt
                if not ts:
                    continue

                # inclusive filter using event timestamp
                if not _in_range_inclusive(ts, start, end):
                    continue

                # update min/max event times
                if min_ts is None or ts < min_ts:
                    min_ts = ts
                if max_ts is None or ts > max_ts:
                    max_ts = ts

                meta_ev = ev.get("meta") or {}
                eid = _extract_entity_id(meta_ev)
                if not eid:
                    continue

                seen_ids.add(eid)

                etype = ev.get("type")
                if etype == EVENT_NEW:
                    # record earliest new ts
                    prev = first_new_ts.get(eid)
                    if prev is None or ts < prev:
                        first_new_ts[eid] = ts
                    # week bucket unique
                    wk = _monday_of(ts)
                    new_week_unique[wk].add(eid)

                elif etype == EVENT_INTERACTION :
                    # record earliest interaction ts
                    prev_i = first_interaction_ts.get(eid)
                    if prev_i is None or ts < prev_i:
                        first_interaction_ts[eid] = ts
                    interaction_counts[eid] += 1
                    wk = _monday_of(ts)
                    interaction_week_unique[wk].add(eid)

        total_ids = set(seen_ids) | set(interaction_counts.keys()) | set(first_new_ts.keys())
        new_ids = set(first_new_ts.keys())

        # Determine returning ids
        returning_ids: Set[str] = set()
        for eid in total_ids:
            if eid in new_ids:
                # has a NEW event in period
                fi = first_interaction_ts.get(eid)
                fn = first_new_ts.get(eid)
                # Only count as returning if there's an interaction after the creation DATE
                if fi and fn and fi.date() > fn.date():
                    returning_ids.add(eid)
            else:
                # no new in period, but has interaction(s)
                if interaction_counts.get(eid, 0) > 0:
                    returning_ids.add(eid)

        # totals
        total_customers = len(total_ids)
        returning_customers = len(returning_ids)
        total_interactions = sum(interaction_counts.values())
        avg_visits = round((total_interactions / total_customers) if total_customers else 0.0, 2)

        # Build weekly series (unique per week)
        if start:
            week_start = _monday_of(start)
        elif min_ts:
            week_start = _monday_of(min_ts)
        else:
            week_start = _monday_of(datetime.now() - timedelta(weeks=11))

        if end:
            week_end_dt = _monday_of(end)
        elif max_ts:
            week_end_dt = _monday_of(max_ts)
        else:
            week_end_dt = _monday_of(datetime.now())

        if week_end_dt < week_start:
            week_end_dt = week_start

        labels: List[str] = []
        counts: List[int] = []
        returning_counts: List[int] = []

        cur = week_start
        while cur <= week_end_dt:
            labels.append(cur.date().isoformat())
            # new unique that week
            counts.append(len(new_week_unique.get(cur, set())))
            # returning unique that week: include only those interaction eids that qualify as returning
            week_interactions = interaction_week_unique.get(cur, set())
            week_returning = {eid for eid in week_interactions if eid in returning_ids}
            returning_counts.append(len(week_returning))
            cur = cur + timedelta(days=7)

        result = {
            "total_customers": total_customers,
            "returning_customers": returning_customers,
            "avg_visits_per_customer": avg_visits,
            "clients" : list(total_ids),
            "weekly": {
                "labels": labels,
                "counts": counts,
                "returning_counts": returning_counts,
            },
        }

        logger.debug(
            "period_customer_stats user=%s start=%s end=%s result=%s",
            binder.current_user,
            start,
            end,
            {"total": total_customers, "returning": returning_customers, "avg_visits": avg_visits},
        )

        return result


MetricRegistry.register(TotalCustomersMetric)
