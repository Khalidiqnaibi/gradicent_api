"""
low_ltv_constraint.py
---------------------
Detects when customers' lifetime value is too low to support growth.

Required metrics:
- ltv
- purchase_frequency
- avg_transaction_value
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class LowLTVConstraint:
    name = "low_ltv"
    required_metrics = ["ltv", "purchase_frequency", "avg_transaction_value"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        ltv = float(metrics.get("ltv", {}).get("ltv", 0) or 0)
        freq = float(metrics.get("purchase_frequency", {}).get("avg_purchases_per_customer", 0) or 0)
        avg_tx = float(metrics.get("avg_transaction_value", {}).get("avg_transaction_value", 0) or 0)

        if ltv < 500:
            base = 9.0
        elif ltv < 1500:
            base = 6.0
        elif ltv < 3000:
            base = 3.0
        else:
            base = 1.0

        # low avg tx increases urgency
        if avg_tx < 50 and freq < 1:
            base += 1.5

        score = round(min(10.0, base), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ltv": metrics.get("ltv", {}),
            "avg_transaction_value": metrics.get("avg_transaction_value", {}),
            "purchase_frequency": metrics.get("purchase_frequency", {}),
            "rationale": [
                f"LTV {metrics.get('ltv', {}).get('ltv')}",
                f"Avg tx {metrics.get('avg_transaction_value', {}).get('avg_transaction_value')}",
                f"Purchases {metrics.get('purchase_frequency', {}).get('avg_purchases_per_customer')}"
            ]
        }


register_constraint(LowLTVConstraint())
