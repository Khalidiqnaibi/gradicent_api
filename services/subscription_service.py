"""
subscription_service.py
------------------------
Handles subscription logic and payment plan management.
Follows SOLID and Gradicent code standards.

- SRP: Manages only subscription domain logic.
- DIP: Depends on adapter and payment provider abstractions.
"""

from typing import Dict, Any, Optional
from config import PLANS


class SubscriptionService:
    """
    Handles subscription upgrades, downgrades, and cancellations.
    """

    def __init__(self, adapter, payment_service):
        self.adapter = adapter
        self.payment_service = payment_service

    def get_plan_price(self, plan_name: str) -> float:
        """Retrieve the cost of a plan."""
        return PLANS.get(plan_name.lower())

    def subscribe_user(self, domain:str, user_id: str, plan_name: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subscribes a user to a selected plan.
        """
        plan_price = self.get_plan_price(plan_name)
        if not plan_price:
            raise ValueError("Invalid plan selected.")

        payment_result = self.payment_service.process_payment(payment_data, plan_price)

        if payment_result["status"] == "success":
            self.adapter.update(domain,user_id,"plan", plan_name)
            return {"status": "success", "data":{"plan": plan_name, "price": plan_price},
                    "message": f"Payment successfull. Amount: {plan_price} , Id: {user_id}"}
        else:
            return {"status": "failed","data":{}, "message": "Payment failed."}

    def cancel_subscription(self,domain:str, user_id: str) -> None:
        """
        Cancels user's subscription and updates metadata.
        """
        self.adapter.update(domain,user_id, "plan", "canceled")
