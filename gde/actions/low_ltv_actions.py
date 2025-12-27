"""
low_ltv_actions.py
------------------
Actions to increase customer lifetime value.
"""

from gde.gde_registry import register_action


class LowLTVActions:
    constraint_name = "low_ltv"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Increase value per customer",
            "steps": [
                "Add upsells",
                "Bundle services",
                "Introduce higher tier plan",
                "Extend retention offers"
            ],
            "expected_result": "Higher LTV"
        }


register_action(LowLTVActions())
