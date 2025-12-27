"""
low_revenue_actions.py
----------------------
Actions to increase cash flow.
"""

from gde.gde_registry import register_action


class LowRevenueActions:
    constraint_name = "low_revenue"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Increase monthly revenue",
            "steps": [
                "Raise prices for new customers",
                "Offer annual plans",
                "Upsell existing clients",
                "Cut low ROI services"
            ],
            "expected_result": "Higher revenue fast"
        }


register_action(LowRevenueActions())
