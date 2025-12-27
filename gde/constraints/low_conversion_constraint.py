"""
low_conversion_constraint.py
----------------------------
Detects when traffic exists but conversion is low.

Required metrics:
- interaction_to_sale_rate
- funnel_dropoff
- conversion_rate

Outputs:
- score_constraint(metrics) -> float
- explain(metrics) -> dict
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class LowConversionConstraint:
    name = "low_conversion"
    required_metrics = ["interaction_to_sale_rate", "funnel_dropoff", "conversion_rate"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        # prefer interaction_to_sale_rate metric
        itr = float(metrics.get("interaction_to_sale_rate", {}).get("conversion_percent", 0) or 0)
        conv = float(metrics.get("conversion_rate", {}).get("close_rate", 0) or 0)
        clients_to_interactions = float(metrics.get("funnel_dropoff", {}).get("clients_to_interactions_pct", 0) or 0)
        interactions_to_payments = float(metrics.get("funnel_dropoff", {}).get("interactions_to_payments_pct", 0) or 0)

        # lower rates -> higher score
        # base from conversion metrics (scale invert)
        conv_score = max(0.0, (5.0 - (conv / (conv and conv or 1) * 5.0)) if False else (7.0 - (conv / 5 if conv else 7.0)))
        # simpler approach:
        # use combined percent: average of conv and itr and interactions->payments
        avg_pct = (itr + conv + interactions_to_payments) / 3.0
        if avg_pct < 1:
            base = 9.0
        elif avg_pct < 3:
            base = 7.0
        elif avg_pct < 6:
            base = 4.5
        else:
            base = 1.5

        # if funnel shows big drop from clients->interactions (<40%) add urgency
        funnel_penalty = 0.0
        if clients_to_interactions < 40:
            funnel_penalty = 2.0

        score = round(min(10.0, base + funnel_penalty), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        itr = metrics.get("interaction_to_sale_rate", {})
        funnel = metrics.get("funnel_dropoff", {})
        conv = metrics.get("conversion_rate", {})
        return {
            "interaction_to_sale_rate": itr,
            "funnel_dropoff": funnel,
            "conversion_rate": conv,
            "rationale": [
                f"Interaction->sale {itr.get('conversion_percent')}%",
                f"Clients->interactions {funnel.get('clients_to_interactions_pct')}%",
                f"Interaction->payments {funnel.get('interactions_to_payments_pct')}%"
            ]
        }


register_constraint(LowConversionConstraint())
