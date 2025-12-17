"""
roi_metric.py
-------------
Computes ROI: (hours_saved * hourly_rate) - subscription_cost.
"""

from typing import Dict, Any
from datetime import datetime
from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry
from ..utils import parse_date


class RoiMetric(IMetric):
    @property
    def name(self) -> str:
        return "roi"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        start = parse_date(kwargs.get("From"))
        end = parse_date(kwargs.get("To"))
        hourly_rate = float(kwargs.get("avg_hourly", 50))
        plan_price = float(kwargs.get("subscription_price", 0))

        # Example dummy logic using binder data
        time_logs = binder.adapter.list_children(binder.domain,binder.current_user, "time_tracking")
        total_seconds = sum(float(l.get("seconds", 0)) for l in time_logs)

        hours_saved = total_seconds / 3600.0
        binder_roi = round(hours_saved * hourly_rate - plan_price, 2)

        return {
            "hours_saved": hours_saved,
            "roi": binder_roi,
            "plan_cost": plan_price,
        }


# Auto-register
MetricRegistry.register(RoiMetric)
