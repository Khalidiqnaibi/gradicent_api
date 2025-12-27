"""
data_visibility_constraint.py
-----------------------------
Detects when the business lacks reliable, recent tracking.

Required metrics:
- tracking_coverage
- data_freshness
- missing_fields_rate

Outputs:
- score_constraint(metrics) -> float (0-10)
- explain(metrics) -> dict (coverage, days_since_last_event, missing_rate, rationale)
"""

from typing import Dict, Any
from gde.gde_registry import register_constraint


class DataVisibilityConstraint:
    name = "data_visibility"
    required_metrics = ["tracking_coverage", "data_freshness", "missing_fields_rate"]

    def _get_safe(self, metrics: Dict[str, Any], key: str, default=0):
        return metrics.get(key, {}).get(next(iter(metrics.get(key, {})), ""), metrics.get(key, default)) if False else metrics.get(key, default)

    def score_constraint(self, metrics: Dict[str, Any]) -> float:
        """
        Higher score = more urgent (0..10).
        - coverage low -> urgent
        - freshness stale -> urgent
        - missing fields high -> urgent
        """
        cov = float(metrics.get("tracking_coverage", {}).get("coverage_percent", 0) or 0)
        days = metrics.get("data_freshness", {}).get("days_since_last_event")
        missing = float(metrics.get("missing_fields_rate", {}).get("missing_rate_percent", 0) or 0)

        # coverage contribution (inverse)
        cov_score = max(0, (100 - cov) / 10)  # 0..10 when coverage 100->0, 0->10

        # freshness contribution
        if days is None:
            fresh_score = 3.0  # unknown freshness is medium concern
        else:
            if days <= 1:
                fresh_score = 0.0
            elif days <= 7:
                fresh_score = 2.0
            elif days <= 30:
                fresh_score = 4.0
            else:
                fresh_score = 7.0

        # missing fields contribution
        missing_score = min(8.0, missing / 12.5)  # missing 0->0, 50% -> 4, 100% -> 8

        raw = cov_score * 0.5 + fresh_score * 0.3 + missing_score * 0.2
        score = round(min(10.0, raw + 0.0), 2)
        return float(score)

    def explain(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Return short diagnostic for UI or logs."""
        cov = metrics.get("tracking_coverage", {}).get("coverage_percent", None)
        days = metrics.get("data_freshness", {}).get("days_since_last_event", None)
        missing = metrics.get("missing_fields_rate", {}).get("missing_rate_percent", None)

        rationale = []
        if cov is None or cov < 60:
            rationale.append(f"Low coverage: {cov}%")
        if days is None or (days is not None and days > 7):
            rationale.append(f"Data stale: {days} days since last event")
        if missing is not None and missing > 20:
            rationale.append(f"Many missing fields: {missing}%")

        return {
            "coverage_percent": cov,
            "days_since_last_event": days,
            "missing_rate_percent": missing,
            "rationale": rationale or ["Data visibility within acceptable bounds"]
        }


# register instance
register_constraint(DataVisibilityConstraint())
