"""
operational_overload_constraint.py
---------------------------------
Detects when operations or people-time are blocking growth.

Required metrics:
- employee_load
- manual_work_ratio
- revenue_per_employee

Outputs:
- score_constraint(metrics) -> float
- explain(metrics) -> dict
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class OperationalOverloadConstraint:
    name = "operational_overload"
    required_metrics = ["employee_load", "manual_work_ratio", "revenue_per_employee"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        avg_load = float(metrics.get("employee_load", {}).get("avg_load", 0) or 0)
        manual_pct = float(metrics.get("manual_work_ratio", {}).get("manual_ratio_percent", 0) or 0)
        rev_per_emp = float(metrics.get("revenue_per_employee", {}).get("revenue_per_employee", 0) or 0)

        # base by load
        if avg_load > 70:
            base = 9.5
        elif avg_load > 55:
            base = 7.0
        elif avg_load > 40:
            base = 4.0
        else:
            base = 1.0

        # manual work amplifies urgency
        manual_amp = 0.0
        if manual_pct > 30:
            manual_amp = 2.0
        elif manual_pct > 15:
            manual_amp = 1.0

        # low revenue per employee increases severity
        rev_amp = 0.0
        if rev_per_emp and rev_per_emp < 2000:
            rev_amp = 1.5

        score = round(min(10.0, base + manual_amp + rev_amp), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "avg_employee_load": metrics.get("employee_load", {}).get("avg_load"),
            "manual_ratio_percent": metrics.get("manual_work_ratio", {}).get("manual_ratio_percent"),
            "revenue_per_employee": metrics.get("revenue_per_employee", {}).get("revenue_per_employee"),
            "rationale": [
                f"Avg load {metrics.get('employee_load', {}).get('avg_load')}",
                f"Manual work {metrics.get('manual_work_ratio', {}).get('manual_ratio_percent')}%",
                f"Revenue/emp {metrics.get('revenue_per_employee', {}).get('revenue_per_employee')}"
            ]
        }


register_constraint(OperationalOverloadConstraint())
