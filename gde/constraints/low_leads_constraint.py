"""
low_leads_constraint.py
-----------------------
Detects insufficient lead volume or bad lead distribution.

Required metrics:
- lead_volume
- lead_source_distribution

Outputs:
- score_constraint(metrics) -> float
- explain(metrics) -> dict
"""

from typing import Dict, Any
from collections import Counter
from gde.gde_registry import register_constraint


class LowLeadsConstraint:
    name = "low_leads"
    required_metrics = ["lead_volume", "lead_source_distribution"]

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        lead_count = int(metrics.get("lead_volume", {}).get("lead_count", 0) or 0)
        # thresholds tuned for sub-$100k companies
        if lead_count < 20:
            base = 9.0
        elif lead_count < 60:
            base = 6.0
        elif lead_count < 150:
            base = 3.0
        else:
            base = 1.0

        # if all leads come from single source -> increase urgency
        dist = metrics.get("lead_source_distribution", {}).get("distribution", {}) or {}
        most = 0
        total = sum(dist.values()) or lead_count
        if total:
            most = max(dist.values()) if dist else 0
            concentration = (most / total) * 100
        else:
            concentration = 0.0

        concentration_penalty = 0.0
        if concentration >= 80:
            concentration_penalty = 2.0
        elif concentration >= 60:
            concentration_penalty = 1.0

        score = round(min(10.0, base + concentration_penalty), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        lead_count = int(metrics.get("lead_volume", {}).get("lead_count", 0) or 0)
        dist = metrics.get("lead_source_distribution", {}).get("distribution", {}) or {}
        # top sources
        top = sorted(dist.items(), key=lambda x: -x[1])[:3]
        return {
            "lead_count": lead_count,
            "top_sources": top,
            "rationale": [
                f"Lead volume = {lead_count}",
                f"Top sources = {top or 'none'}"
            ]
        }


register_constraint(LowLeadsConstraint())
