"""
low_conversion_actions.py
-------------------------
Actions to increase sales conversion.
"""

from gde.gde_registry import register_action


class LowConversionActions:
    constraint_name = "low_conversion"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Turn leads into customers",
            "steps": [
                "Fix offer clarity",
                "Add urgency to CTA",
                "Improve sales script",
                "Handle top 3 objections"
            ],
            "expected_result": "Higher close rate"
        }


register_action(LowConversionActions())
