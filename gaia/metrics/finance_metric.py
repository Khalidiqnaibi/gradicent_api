"""
finance_metric.py
-----------------
Computes total revenue, unpaid balance, and average revenue per client.
"""

from typing import Dict, Any
from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry


class FinanceMetric(IMetric):
    @property
    def name(self) -> str:
        return "finance"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        total_revenue = 0.0
        total_unpaid = 0.0
        patients = binder.adapter.list_children(binder.current_user, "clients")

        for p in patients:
            visits = binder.adapter.list_nested(binder.current_user, "clients", p["id"], "transactions")
            for v in visits:
                total_revenue += float(v.get("payed", 0))
                total_unpaid += float(v.get("debit", 0))

        avg_revenue = total_revenue / max(len(patients), 1)

        return {
            "total_revenue": round(total_revenue, 2),
            "total_unpaid": round(total_unpaid, 2),
            "avg_revenue_per_client": round(avg_revenue, 2),
        }


MetricRegistry.register(FinanceMetric)
