"""
data_visibility_actions.py
--------------------------
Actions to establish basic tracking.
"""

from gde.gde_registry import register_action


class DataVisibilityActions:
    constraint_name = "data_visibility"

    def get_action_plan(self) -> dict:
        return {
            "goal": "See the business clearly",
            "steps": [
                "Track leads, sales, churn, revenue",
                "Set weekly metric review",
                "Connect all data sources to Binder",
                "Remove unused metrics"
            ],
            "expected_result": "Clear numbers for decision making"
        }


register_action(DataVisibilityActions())
