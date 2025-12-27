"""
gde_engine.py
-------------
Core decision engine.

Why this exists:
- Combines GAIA metrics with constraints
- Determines the most urgent business bottleneck
"""

from gaia import GaiaEngine
from gde.gde_registry import get_constraints, get_actions_for_constraint


class GDEngine:
    """
    Gradicent Decision Engine.
    """

    def __init__(self):
        self.gaia_engine = GaiaEngine()

    def analyze_business(self, binder) -> dict:
        """
        Analyze a business and return the most urgent constraint
        with actionable steps.

        Args:
            binder: Binder instance with current_user set

        Returns:
            dict: Decision output
        """
        metrics = self._collect_metrics(binder)
        top_constraint, urgency = self._find_top_constraint(metrics)
        actions = self._get_actions(top_constraint)

        return {
            "constraint": top_constraint.name,
            "urgency_score": urgency,
            "actions": actions
        }

    def _collect_metrics(self, binder) -> dict:
        """
        Collect all required GAIA metrics.

        Returns:
            dict: metric_name -> metric_data
        """
        metrics = {}

        for constraint in get_constraints():
            for metric in constraint.required_metrics:
                if metric not in metrics:
                    metrics[metric] = self.gaia_engine.compute(binder, metric)

        return metrics

    def _find_top_constraint(self, metrics: dict):
        scored = []

        for constraint in get_constraints():
            score = constraint.score_constraint(metrics)
            scored.append((constraint, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0]

    def _get_actions(self, constraint):
        actions = get_actions_for_constraint(constraint.name)
        return [a.get_action_plan() for a in actions]
