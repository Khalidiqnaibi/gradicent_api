"""
high_churn_constraint.py
------------------------
Detects high churn and low customer lifetime.

Required metrics:
- churn_rate
- customer_lifetime_days
- purchase_frequency
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class HighChurnConstraint:
    name = "high_churn"
    required_metrics = ["churn_rate", "customer_lifetime_days", "purchase_frequency"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        churn = float(metrics.get("churn_rate", {}).get("churn_rate_percent", 0) or 0)
        lifetime = metrics.get("customer_lifetime_days", {}).get("avg_customer_lifetime_days", None)
        purchase_freq = float(metrics.get("purchase_frequency", {}).get("avg_purchases_per_customer", 0) or 0)

        # churn-driven scoring
        if churn >= 15:
            base = 9.5
        elif churn >= 8:
            base = 7.0
        elif churn >= 4:
            base = 4.0
        else:
            base = 1.0

        # short lifetime and low frequency amplify urgency
        amp = 0.0
        if lifetime is not None and lifetime < 90:
            amp += 1.5
        if purchase_freq < 1:
            amp += 1.0

        score = round(min(10.0, base + amp), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "churn_rate": metrics.get("churn_rate", {}),
            "avg_customer_lifetime_days": metrics.get("customer_lifetime_days", {}),
            "purchase_frequency": metrics.get("purchase_frequency", {}),
            "rationale": [
                f"Churn {metrics.get('churn_rate', {}).get('churn_rate_percent')}",
                f"Lifetime {metrics.get('customer_lifetime_days', {}).get('avg_customer_lifetime_days')}",
                f"Purchase frequency {metrics.get('purchase_frequency', {}).get('avg_purchases_per_customer')}"
            ]
        }


register_constraint(HighChurnConstraint())
