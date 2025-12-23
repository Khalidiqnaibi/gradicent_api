"""
total_customers_metric.py
-------------------------
Event-driven counts for a time period + weekly series.

Returns:
- total_customers
- returning_customers
- avg_visits_per_customer
- weekly: { labels, counts (new), returning_counts }
"""

from typing import Dict, Any, Set, DefaultDict, List
from collections import defaultdict
import logging
from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from gaia.utils import parse_date

logger = logging.getLogger(__name__)

# Per your note:
EVENT_NEW = 201
EVENT_RETURNING = 202
EVENT_INTERACTION = 202


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
        """
        Required kwargs (optional; if missing, treats as unbounded):
            start_date / From : inclusive start timestamp (ISO or YYYY-MM-DD)
            end_date   / To   : inclusive end timestamp (ISO or YYYY-MM-DD)
            domain (optional) : not required for events-only counts

        Returns:
            {
              "total_customers": int,
              "returning_customers": int,
              "avg_visits_per_customer": float,
              "weekly": { "labels": [...], "counts": [...], "returning_counts": [...] }
            }
        """
        # parse inclusive start/end
        start = parse_date(kwargs.get("start_date") or kwargs.get("from") or kwargs.get("From"))
        end = parse_date(kwargs.get("end_date") or kwargs.get("to") or kwargs.get("To"))

        # load analytics (structure: analytics[day]['events'] = [...])
        meta = binder.adapter.get_child(binder.domain, binder.current_user, "metadata") or {}
        analytics = meta.get("analytics", {}) or {}

        # per-entity counters derived directly from events
        interaction_counts: DefaultDict[str, int] = defaultdict(int)
        new_ids: Set[str] = set()
        returning_ids: Set[str] = set()
        seen_ids: Set[str] = set()

        # For weekly aggregation
        new_week: DefaultDict[datetime, int] = defaultdict(int)
        returning_week: DefaultDict[datetime, int] = defaultdict(int)

        # Track min/max event timestamps seen (for building week range if start/end missing)
        min_ts: datetime = None
        max_ts: datetime = None

        # Single pass over analytics -> days -> events
        for day_key, payload in analytics.items():
            # day_key is typically "YYYY-MM-DD"; events have full timestamps
            day_dt = parse_date(day_key)

            # optional day pruning (quick skip whole-day if outside)
            if day_dt:
                if start and day_dt.date() < start.date():
                    continue
                if end and day_dt.date() > end.date():
                    continue

            for ev in payload.get("events", []) or []:
                # Prefer event timestamp for precise inclusion
                ts = _parse_iso_ts(ev.get("timestamp"))
                if not ts:
                    # fallback: if no event timestamp, use day_dt
                    ts = day_dt
                if not ts:
                    continue

                if not _in_range_inclusive(ts, start, end):
                    continue

                # update min/max
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
                    new_ids.add(eid)
                    # weekly bucket
                    wk = _monday_of(ts)
                    new_week[wk] += 1
                elif etype == EVENT_RETURNING:
                    returning_ids.add(eid)
                    wk = _monday_of(ts)
                    returning_week[wk] += 1
                elif etype == EVENT_INTERACTION:
                    # count one interaction occurrence
                    interaction_counts[eid] += 1

        # total customers: unique entities seen in the period
        total_ids = set(interaction_counts.keys()) | new_ids | returning_ids | seen_ids
        total_customers = len(total_ids)

        # returning customers count (per your required mapping)
        returning_customers = sum(1 for eid in total_ids if eid in returning_ids)

        # average visits per customer: interactions / customers (0 if none)
        total_interactions = sum(interaction_counts.values())
        avg_visits = round((total_interactions / total_customers) if total_customers else 0.0, 2)

        # Build weekly series:
        # Determine week range: use provided start/end if present, else use min_ts/max_ts (or last 12 weeks)
        if start:
            week_start = _monday_of(start)
        elif min_ts:
            week_start = _monday_of(min_ts)
        else:
            # fallback to 12 weeks ending this week
            today = datetime.now()
            week_start = _monday_of(today - timedelta(weeks=11))

        if end:
            week_end_dt = _monday_of(end)
        elif max_ts:
            week_end_dt = _monday_of(max_ts)
        else:
            week_end_dt = _monday_of(datetime.now())

        # Ensure week_end_dt >= week_start
        if week_end_dt < week_start:
            week_end_dt = week_start

        # produce week labels (inclusive)
        labels: List[str] = []
        counts: List[int] = []
        returning_counts: List[int] = []

        cur = week_start
        while cur <= week_end_dt:
            labels.append(cur.date().isoformat())
            counts.append(new_week.get(cur, 0))
            returning_counts.append(returning_week.get(cur, 0))
            cur = cur + timedelta(days=7)

        result = {
            "total_customers": total_customers,
            "returning_customers": returning_customers,
            "avg_visits_per_customer": avg_visits,
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
