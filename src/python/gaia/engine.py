from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .adapter import DomainAdapter
from .utils import parse_date_or_timestamp, in_range_dt, matches_entity_filter
from .exceptions import MetricNotFoundError

import logging
logger = logging.getLogger("gaia.engine")
logger.setLevel(logging.INFO)

class GaiaEngine:
    """
    GaiaEngine coordinates adapters and metric handlers.
    SOLID notes:
      - Single Responsibility: orchestrates metrics, not data access (adapter handles that).
      - Open/Closed: metrics are registerable via register_metric.
      - Dependency Inversion: depends on DomainAdapter interface (protocol).
    """

    def __init__(self, adapter: DomainAdapter, *, config: Optional[Dict[str, Any]] = None):
        self.adapter = adapter
        self.config = config or {}
        self._metrics: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {}
        # register built-ins
        self.register_metric("roi", self._metric_roi)
        self.register_metric("productivity", self._metric_productivity)
        self.register_metric("finance", self._metric_finance)
        self.register_metric("entities", self._metric_entities)  # formerly patients

    def register_metric(self, name: str, handler: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Register a metric handler. New metrics can be added without modifying engine internals.
        """
        self._metrics[name] = handler

    def compute(self, metric_name: str, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handler = self._metrics.get(metric_name)
        if not handler:
            raise MetricNotFoundError(metric_name)
        logger.info("Computing metric '%s' for user '%s' with params %s", metric_name, user_id, params)
        return handler(user_id, params)

    # ------------------- Metric Implementations -------------------
    def _metric_roi(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        start = parse_date_or_timestamp(params.get("from"), None)
        end = parse_date_or_timestamp(params.get("to"), None)
        entity = params.get("entity") or params.get("patient")
        if end and start and end < start:
            start, end = end, start

        IGNORED = params.get("ignored_types", ["page viewed"])

        time_logs = self.adapter.fetch_time_logs(user_id) or []
        total_seconds = 0.0
        for rec in time_logs:
            try:
                if rec.get("user") != user_id:
                    continue
                if rec.get("type") in IGNORED:
                    continue
                # entity-aware filtering only when entity info exists
                if entity:
                    fields = [rec.get(pk) for pk in ("entity","patient","patient_id","id","name")]
                    if any(fields):
                        if not any(str(v) == str(entity) for v in fields if v):
                            if not matches_entity_filter(entity, rec):
                                continue
                ts_dt = parse_date_or_timestamp(rec.get("timestamp"), None)
                if (start or end) and (not ts_dt or not in_range_dt(ts_dt, start, end)):
                    continue
                total_seconds += float(rec.get("seconds", 0) or 0)
            except Exception:
                continue
        hours_saved = round(total_seconds / 3600.0, 2)

        analytics = self.adapter.fetch_analytics(user_id) or []
        tasks_counter = Counter()
        for ev in analytics:
            try:
                if ev.get("user") != user_id:
                    continue
                if ev.get("type") in IGNORED:
                    continue
                if entity:
                    fields = [ev.get(pk) for pk in ("entity","patient","patient_id","id","name")]
                    if any(fields):
                        if not any(str(v) == str(entity) for v in fields if v):
                            if not matches_entity_filter(entity, ev):
                                continue
                ts_dt = parse_date_or_timestamp(ev.get("timestamp"), None)
                if (start or end) and (not ts_dt or not in_range_dt(ts_dt, start, end)):
                    continue
                typ = ev.get("type", "other")
                tasks_counter[typ] += 1
            except Exception:
                continue

        avg_hourly = float(params.get("avg_hourly", self.config.get("default_avg_hourly", 50)))
        user_doc = self.adapter.fetch_user_doc(user_id) or {}
        plan = user_doc.get("plan", "free")
        plan_map = self.config.get("plan_price_map", {})
        subscription_price = float(plan_map.get(plan, 0))

        binder_roi = round(hours_saved * avg_hourly - subscription_price, 2)

        if start and end:
            window_days = max(1, (end.date() - start.date()).days)
        else:
            window_days = 30
        daily_savings = (hours_saved * avg_hourly) / max(1, window_days)
        payback_days = int(subscription_price / (daily_savings or 1)) if daily_savings > 0 else None

        return {
            "hours_saved": hours_saved,
            "binder_roi": binder_roi,
            "subscription_price": subscription_price,
            "payback_days": payback_days,
            "tasks": dict(tasks_counter)
        }

    def _metric_productivity(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        start = parse_date_or_timestamp(params.get("from"), None)
        end = parse_date_or_timestamp(params.get("to"), None)
        entity = params.get("entity") or params.get("patient")
        if end and start and end < start:
            start, end = end, start

        time_logs = self.adapter.fetch_time_logs(user_id) or []
        analytics = self.adapter.fetch_analytics(user_id) or []

        total_seconds = 0.0
        for l in time_logs:
            if l.get("user") != user_id:
                continue
            if entity:
                if not any(str(l.get(pk)) == str(entity) for pk in ("entity","patient","patient_id","id","name")):
                    if not matches_entity_filter(entity, l):
                        continue
            ts_dt = parse_date_or_timestamp(l.get("timestamp"), None)
            if start or end:
                if not ts_dt or not in_range_dt(ts_dt, start, end):
                    continue
            total_seconds += float(l.get("seconds", 0) or 0)
        total_minutes = round(total_seconds / 60.0, 2)

        session_dates = set()
        for l in time_logs:
            if l.get("user") != user_id: continue
            ts_dt = parse_date_or_timestamp(l.get("timestamp"), None)
            if start or end:
                if not ts_dt or not in_range_dt(ts_dt, start, end):
                    continue
            if ts_dt:
                session_dates.add(ts_dt.date().isoformat())
        session_count = max(1, len(session_dates))
        avg_per_session = round(total_minutes / session_count, 2)

        productive_seconds = 0.0
        for l in time_logs:
            if l.get("user") != user_id: continue
            ts_dt = parse_date_or_timestamp(l.get("timestamp"), None)
            if start or end:
                if not ts_dt or not in_range_dt(ts_dt, start, end):
                    continue
            if not ts_dt: continue
            if 8 <= ts_dt.hour < 18:
                productive_seconds += float(l.get("seconds", 0) or 0)
        percent_productive = round((productive_seconds / (total_seconds or 1)) * 100, 1)

        visits = 0
        for ev in analytics:
            if ev.get("user") != user_id: continue
            if ev.get("type") != "New Visit": continue
            if entity:
                matched = False
                for pk in ("entity", "patient", "patient_id", "id", "name"):
                    if str(ev.get(pk)) == str(entity):
                        matched = True
                        break
                if not matched and not matches_entity_filter(entity, ev):
                    continue
            ts_dt = parse_date_or_timestamp(ev.get("timestamp"), None)
            if start or end:
                if not ts_dt or not in_range_dt(ts_dt, start, end):
                    continue
            visits += 1

        active_hours = max(0.01, total_seconds / 3600.0)
        visits_per_active_hour = round(visits / active_hours, 2)

        now = datetime.now()
        by_day = {}
        for l in time_logs:
            if l.get("user") != user_id: continue
            ts_dt = parse_date_or_timestamp(l.get("timestamp"), None)
            if not ts_dt:
                continue
            if start or end:
                if not in_range_dt(ts_dt, start, end):
                    continue
            if not (start or end) and (now.date() - ts_dt.date()).days > 30:
                continue
            key = ts_dt.date().isoformat()
            by_day.setdefault(key, {"minutes": 0, "entities": 0})
            by_day[key]["minutes"] += float(l.get("seconds", 0) or 0) / 60.0

        for ev in analytics:
            if ev.get("user") != user_id: continue
            if ev.get("type") != "New Patient": continue
            ts_dt = parse_date_or_timestamp(ev.get("timestamp"), None)
            if not ts_dt: continue
            if start or end:
                if not in_range_dt(ts_dt, start, end):
                    continue
            if not (start or end) and (now.date() - ts_dt.date()).days > 30:
                continue
            key = ts_dt.date().isoformat()
            by_day.setdefault(key, {"minutes": 0, "entities": 0})
            by_day[key]["entities"] += 1

        labels = sorted(by_day.keys())
        minutes = [round(by_day[d]["minutes"], 2) for d in labels]
        entities = [by_day[d]["entities"] for d in labels]
        return {
            "total_time_minutes": total_minutes,
            "avg_time_per_session_minutes": avg_per_session,
            "percent_productive": percent_productive,
            "visits_per_active_hour": visits_per_active_hour,
            "time_vs_entities": {"labels": labels, "minutes": minutes, "entities": entities}
        }

    def _metric_finance(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        start = parse_date_or_timestamp(params.get("from"), None)
        end = parse_date_or_timestamp(params.get("to"), None)
        if end and start and end < start:
            start, end = end, start
        entity = params.get("entity") or params.get("patient")

        dr = self.adapter.fetch_user_doc(user_id) or {}
        entities = dr.get("patients") if isinstance(dr.get("patients", []), list) else dr.get("entities", [])

        total_revenue = 0.0
        total_unpaid = 0.0
        per_entity = {}

        for p in entities or []:
            pid = p.get("id") or p.get("name", "unknown")
            if entity and not matches_entity_filter(entity, p):
                continue
            for v in p.get("visits", []) or []:
                vdate = v.get("visit_date")
                vdt = parse_date_or_timestamp(vdate, None)
                if start or end:
                    if not vdt or not in_range_dt(vdt, start, end):
                        continue
                payed = float(v.get("payed", 0) or 0)
                debit = float(v.get("debit", 0) or 0)
                total_revenue += payed
                total_unpaid += debit
                per_entity[pid] = per_entity.get(pid, 0) + payed

        avg_per_entity = round(total_revenue / (len(per_entity) or 1), 2)

        trend_map = {}
        for p in entities or []:
            if entity and not matches_entity_filter(entity, p):
                continue
            for v in p.get("visits", []) or []:
                d = v.get("visit_date")
                if not d: continue
                d_dt = parse_date_or_timestamp(d, None)
                if start or end:
                    if not d_dt or not in_range_dt(d_dt, start, end):
                        continue
                key = d_dt.date().isoformat() if d_dt else d
                trend_map.setdefault(key, {"rev": 0.0, "unpaid": 0.0})
                trend_map[key]["rev"] += float(v.get("payed", 0) or 0)
                trend_map[key]["unpaid"] += float(v.get("debit", 0) or 0)

        trend_labels = sorted(trend_map.keys())
        trend_revenue = [round(trend_map[d]["rev"], 2) for d in trend_labels]
        trend_unpaid = [round(trend_map[d]["unpaid"], 2) for d in trend_labels]

        return {
            "total_revenue": round(total_revenue, 2),
            "total_unpaid": round(total_unpaid, 2),
            "avg_revenue_per_entity": avg_per_entity,
            "trend": {"labels": trend_labels, "revenue": trend_revenue, "unpaid": trend_unpaid}
        }

    def _metric_entities(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # generic replacement of patients endpoint
        start = parse_date_or_timestamp(params.get("from"), None)
        end = parse_date_or_timestamp(params.get("to"), None)
        if end and start and end < start:
            start, end = end, start
        entity = params.get("entity") or params.get("patient")

        dr = self.adapter.fetch_user_doc(user_id) or {}
        entities = dr.get("patients", []) if isinstance(dr.get("patients", []), list) else dr.get("entities", [])

        total_set = set()
        returning = 0
        visits_counts = []
        new_this_month = 0
        now = datetime.now()
        diag_counter = Counter()
        treatment_counter = Counter()
        debt_set = set()
        weekly_map = {}

        for p in entities or []:
            pid = p.get("id") or p.get("name", "unknown")
            if entity and not matches_entity_filter(entity, p):
                continue

            filtered_visits = []
            for v in p.get("visits", []) or []:
                vdate = v.get("visit_date")
                v_dt = parse_date_or_timestamp(vdate, None)
                if start or end:
                    if not v_dt:
                        continue
                    if not in_range_dt(v_dt, start, end):
                        continue
                filtered_visits.append((v, v_dt))

            if not filtered_visits:
                continue

            total_set.add(pid)
            vcount = len(filtered_visits)
            visits_counts.append(vcount)
            if vcount > 1:
                returning += 1

            try:
                first_dt = min((vd for (_, vd) in filtered_visits if vd is not None), default=None)
                if first_dt:
                    if (now.date() - first_dt.date()).days <= 30:
                        new_this_month += 1
                    week_start = (first_dt.date() - timedelta(days=first_dt.weekday())).isoformat()
                    weekly_map[week_start] = weekly_map.get(week_start, 0) + 1
            except Exception:
                pass

            owes = False
            for v, v_dt in filtered_visits:
                if float(v.get("debit", 0) or 0) > 0:
                    owes = True
                diag = v.get("diagnosis")
                treat = v.get("treatment")
                if diag: diag_counter[diag] += 1
                if treat: treatment_counter[treat] += 1
            if owes:
                debt_set.add(pid)

        total = len(total_set)
        avg_visits = round(sum(visits_counts) / (total or 1), 2)
        weekly_labels = sorted(weekly_map.keys())[-12:]
        weekly_counts = [weekly_map.get(l, 0) for l in weekly_labels]
        top_diag = [{"name": k, "count": v} for k, v in diag_counter.most_common(8)]
        top_treat = [{"name": k, "count": v} for k, v in treatment_counter.most_common(8)]
        debt_patients = len(debt_set)

        return {
            "total_entities": total,
            "returning_entities": returning,
            "new_entities_month": new_this_month,
            "avg_visits_per_entity": avg_visits,
            "weekly": {"labels": weekly_labels, "counts": weekly_counts},
            "debt_entities": debt_patients,
            "debt_ratio": round((debt_patients / (total or 1)) * 100, 1),
            "top_diagnoses": top_diag,
            "top_treatments": top_treat,
            "top_diagnoses_raw": top_diag
        }
