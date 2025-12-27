"""
low_leads_actions.py
--------------------
Actions to increase inbound volume.
"""

from gde.gde_registry import register_action


class LowLeadsActions:
    constraint_name = "low_leads"

    def get_action_plan(self) -> dict:
        return {
            "goal": "Increase inbound leads",
            "steps": [
                "Launch 1 core acquisition channel",
                "Post daily content",
                "Run simple paid test",
                "Optimize lead magnet"
            ],
            "expected_result": "More people entering funnel"
        }


register_action(LowLeadsActions())
