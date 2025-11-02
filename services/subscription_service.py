'''
subscription_service.py
----------------
Subscription service module for managing user subscriptions and trial periods.    
'''

from typing import Dict
from binder import storage_adapter
from ..payments.payment_provider import IPaymentProvider

class SubscriptionService:
    """
    Handles plan checks, payback/trial and plan upgrades.
    
    expects
        storage (StorageAdapter): Storage adapter for user data.
        payment_provider (PaymentProvider): Payment provider for handling payments.
    outputs
        get_user_plan(user_id: str) -> str: Returns the current plan of the user.
        start_checkout(user_id: str, plan: str, provider: str) -> dict: Starts a checkout session for the user.
        complete_webhook(payload: dict) -> None: Completes the webhook process for payment confirmation.
    """

    def __init__(self, storage: storage_adapter.StorageAdapter, payment_provider: IPaymentProvider):
        self.storage = storage
        self.payment_provider = payment_provider

    def get_user_plan(self, user_id: str) -> str:
        user = self.storage.get(f"users/{user_id}")
        return user.get("plan", "free")

    def start_checkout(self, user_id: str, plan: str, provider: str) -> dict:
        price = self._plan_price(plan)
        return self.payment_provider.create_payment(amount=price, currency='USD', metadata={"user_id": user_id, "plan": plan})

    def complete_webhook(self, payload: dict) -> None:
        # called by webhook route to finalize subscription (update DB)
        pass
