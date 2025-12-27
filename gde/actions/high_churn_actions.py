"""
high_churn_actions.py
---------------------
Actions to reduce customer loss.
"""

from gde.gde_registry import register_action


class HighChurnActions:
    constraint_name = "high_churn"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Keep customers longer",
            "steps": [
                "Improve onboarding",
                "Add weekly check-ins",
                "Fix top churn reason",
                "Set success milestones"
            ],
            "expected_result": "Lower churn"
        }


register_action(HighChurnActions())
