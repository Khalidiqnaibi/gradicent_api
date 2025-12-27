"""
operational_overload_actions.py
-------------------------------
Actions to reduce internal bottlenecks.
"""

from gde.gde_registry import register_action


class OperationalOverloadActions:
    constraint_name = "operational_overload"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Free founder and team time",
            "steps": [
                "Document core processes",
                "Delegate repeat tasks",
                "Automate reporting",
                "Remove non-essential work"
            ],
            "expected_result": "More capacity to grow"
        }


register_action(OperationalOverloadActions())
