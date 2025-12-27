"""
low_revenue_constraint.py
-------------------------
Detects when overall revenue is too low for the company's size and recent trend.

Required metrics:
- finance
- avg_transaction_value
- lead_volume
- ltv
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class LowRevenueConstraint:
    name = "low_revenue"
    required_metrics = ["finance", "avg_transaction_value", "lead_volume", "ltv"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        total_revenue = float(metrics.get("finance", {}).get("total_revenue", 0) or 0)
        avg_tx = float(metrics.get("avg_transaction_value", {}).get("avg_transaction_value", 0) or 0)
        lead_count = int(metrics.get("lead_volume", {}).get("lead_count", 0) or 0)
        ltv = float(metrics.get("ltv", {}).get("ltv", 0) or 0)

        # thresholds are relative; tune for your ICP
        if total_revenue < 3000:
            base = 9.5
        elif total_revenue < 7000:
            base = 6.5
        elif total_revenue < 20000:
            base = 3.0
        else:
            base = 1.0

        # if avg_tx is tiny and leads exist -> higher urgency to increase price or upsells
        tx_penalty = 0.0
        if avg_tx < 50 and lead_count > 0:
            tx_penalty = 1.5
        if ltv and ltv < 500:
            tx_penalty += 1.0

        score = round(min(10.0, base + tx_penalty), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        fin = metrics.get("finance", {})
        avg_tx = metrics.get("avg_transaction_value", {})
        lead = metrics.get("lead_volume", {})
        ltv = metrics.get("ltv", {})
        return {
            "total_revenue": fin.get("total_revenue"),
            "avg_transaction_value": avg_tx.get("avg_transaction_value"),
            "lead_count": lead.get("lead_count"),
            "ltv": ltv.get("ltv"),
            "rationale": [
                f"Revenue {fin.get('total_revenue')}",
                f"Avg transaction {avg_tx.get('avg_transaction_value')}",
                f"Lead volume {lead.get('lead_count')}"
            ]
        }


register_constraint(LowRevenueConstraint())
