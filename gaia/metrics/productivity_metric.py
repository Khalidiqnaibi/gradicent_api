from datetime import datetime, timedelta
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry
from flask import current_app as app
from gaia.utils import filter_patients,filter_clients
from binder import normalize_user

def _parse_date_or_timestamp(value, default):
    if not value:
        return default
    try:
        if len(value) == 10 and value.count("-") == 2:
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(value)
    except Exception:
        return default

def _in_range_dt(ts, start, end):
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True

def _get_clients_user(user):
    user = normalize_user(user)
    user = user.to_dict() or {}
    return user.get("clients",[])

class ProductivityMetric(IMetric):

    @property
    def name(self):
        return "productivity"


    def compute(self, binder, **kwargs):
        '''
        productivity metric for the gaia engin 
        based on the binder user actions

        kwargs:
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

        '''
        # -------------------------------------------
        # 0. Extract domain + base user
        # -------------------------------------------
        DOMAIN = kwargs.get("domain", "medical")
        user   = binder.adapter.get_user(binder.current_user) or {}
        start_dt = kwargs.get("form") or kwargs.get("From") or kwargs.get("start_date")
        end_dt = kwargs.get("to") or kwargs.get("To") or kwargs.get("end_date")

        # -------------------------------------------
        # 1. Select and filter clients
        # -------------------------------------------
        clients = _get_clients_user(user)

        if DOMAIN == "medical":
            matched = filter_patients(clients, kwargs)
        elif DOMAIN == "business":
            matched = filter_clients(clients, kwargs)
        else:
            matched = filter_clients(clients, kwargs)   # fallback

        # -------------------------------------------
        # 2. Aggregate logs from matched clients
        # -------------------------------------------
        time_logs = []
        analytics = []

        for c in matched:
            a = c.get("metadata", {}).get("analatics", {})
            analytics.append(a)
            time_logs.append(a.get("time_tracking", {}) or {})

        # Flatten time logs & events
        flat_time = []
        flat_events = []

        for tblock in time_logs:
            for k, v in (tblock.items() if isinstance(tblock, dict) else []):
                flat_time.append(v)

        for ablock in analytics:
            for k, v in (ablock.items() if isinstance(ablock, dict) else []):
                flat_events.append(v)

        # -------------------------------------------
        # 4. Compute total time
        # -------------------------------------------
        total_seconds = 0.0

        for log in flat_time:
            ts = log.get("timestamp")
            ts_dt = _parse_date_or_timestamp(ts, None)
            if start_dt or end_dt:
                if not ts_dt or not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue
            total_seconds += float(log.get("seconds", 0) or 0)

        total_minutes = round(total_seconds / 60.0, 2)

        # -------------------------------------------
        # 5. Sessions (count unique days)
        # -------------------------------------------
        session_dates = set()

        for log in flat_time:
            ts_dt = _parse_date_or_timestamp(log.get("timestamp"), None)
            if not ts_dt:
                continue
            if start_dt or end_dt:
                if not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue
            session_dates.add(ts_dt.date().isoformat())

        session_count = max(1, len(session_dates))
        avg_per_session = round(total_minutes / session_count, 2)

        # -------------------------------------------
        # 6. Productive time (8–18)
        # -------------------------------------------
        productive_seconds = 0.0

        for log in flat_time:
            ts_dt = _parse_date_or_timestamp(log.get("timestamp"), None)
            if not ts_dt:
                continue
            if start_dt or end_dt:
                if not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue
            if 8 <= ts_dt.hour < 18:
                productive_seconds += float(log.get("seconds", 0) or 0)

        percent_productive = round((productive_seconds / (total_seconds or 1)) * 100, 1)

        # -------------------------------------------
        # 7. Visit analytics (New Visit)
        # -------------------------------------------
        visits = 0
        for ev in flat_events:
            if ev.get("type") != "New Visit":
                continue
            ts_dt = _parse_date_or_timestamp(ev.get("timestamp"), None)
            if not ts_dt:
                continue
            if start_dt or end_dt:
                if not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue
            visits += 1

        active_hours = max(0.01, total_seconds / 3600.0)
        visits_per_active_hour = round(visits / active_hours, 2)

        # -------------------------------------------
        # 8. Build "time vs patient" series
        # -------------------------------------------
        now = datetime.now()
        by_day = {}

        # --- Time logs
        for log in flat_time:
            ts_dt = _parse_date_or_timestamp(log.get("timestamp"), None)
            if not ts_dt:
                continue

            if start_dt or end_dt:
                if not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue

            # if no date filter: last 30 days only
            if not (start_dt or end_dt):
                if (now.date() - ts_dt.date()).days > 30:
                    continue

            key = ts_dt.date().isoformat()
            by_day.setdefault(key, {"minutes": 0, "patients": 0})
            by_day[key]["minutes"] += float(log.get("seconds", 0) or 0) / 60.0

        # --- New Patient analytics
        for ev in flat_events:
            if ev.get("type") != "New Patient":
                continue

            ts_dt = _parse_date_or_timestamp(ev.get("timestamp"), None)
            if not ts_dt:
                continue

            if start_dt or end_dt:
                if not _in_range_dt(ts_dt, start_dt, end_dt):
                    continue

            if not (start_dt or end_dt):
                if (now.date() - ts_dt.date()).days > 30:
                    continue

            key = ts_dt.date().isoformat()
            by_day.setdefault(key, {"minutes": 0, "patients": 0})
            by_day[key]["patients"] += 1

        labels = sorted(by_day.keys())
        minutes = [round(by_day[d]["minutes"], 2) for d in labels]
        patients = [by_day[d]["patients"] for d in labels]

        # -------------------------------------------
        # Return productivity metric
        # -------------------------------------------
        return {
            "total_time_minutes": total_minutes,
            "avg_time_per_session_minutes": avg_per_session,
            "percent_productive": percent_productive,
            "visits_per_active_hour": visits_per_active_hour,
            "time_vs_patients": {
                "labels": labels,
                "minutes": minutes,
                "patients": patients
            }
        }


# Register metric
MetricRegistry.register(ProductivityMetric)
