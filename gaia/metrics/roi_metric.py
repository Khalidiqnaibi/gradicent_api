"""
roi_metric.py
-------------
Computes ROI: (hours_saved * hourly_rate) - subscription_cost.
"""

from tracemalloc import start
from typing import Dict, Any
from datetime import date, datetime
from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry
from ..utils import parse_date
from config import PRO_PRICE,ULTRA_PRICE,PACKAGE_PRICE,STARTER_PRICE, EVENTS

price = {
    "starter" : STARTER_PRICE,
    "ultra" : ULTRA_PRICE,
    "package":PACKAGE_PRICE,
    "pro" : PRO_PRICE,
    "free" :0
}

class RoiMetric(IMetric):
    @property
    def name(self) -> str:
        return "roi"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        start = parse_date(kwargs.get("From",kwargs.get("from")))
        end = parse_date(kwargs.get("To",kwargs.get("to")))
        hourly_rate = float(kwargs.get("avg_hourly", 50))
        plan= kwargs.get("plan", 'free')
        plan_price = float(price.get(plan, 0))

        # Example dummy logic using binder data
        meta = binder.adapter.get_child(binder.domain,binder.current_user, "metadata")
        a = meta.get("analytics",{})
        total_seconds = 0
        for i in a.keys():
            d = parse_date(i)

            if start and d < start:
                continue
            if end and d > end:
                continue

            total_seconds += sum(
            float(l.get("seconds", 0)) 
            for l in a[i].get("time_tracking", [])
    )
        hours_saved = total_seconds / 3600.0
        binder_roi = round(hours_saved * hourly_rate - plan_price, 2)
        events = []
        for i in a:
            date = parse_date(i)

            if start and d < start:
                continue
            if end and d > end:
                continue
            for j in a[i].get("events", []):
                total_seconds += float(j.get("seconds_saved", 0))
                res = j.copy()
                res["type"] = EVENTS.get(j.get("type", 100), "Unknown")
                events.append(res)

        return {
            "hours_saved": hours_saved,
            "roi": binder_roi,
            "plan_cost": plan_price,
            "payback_period_hours": round(plan_price / hourly_rate, 2) if hourly_rate > 0 else None,
            "tasks": events
        }


# Auto-register
MetricRegistry.register(RoiMetric)
