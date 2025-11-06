"""
payment_service.py
-------------------
Manages payment operations across providers (Stripe, PayPal, Paddle).

- SRP: Handles only payment orchestration.
- OCP: New providers can be added without modifying core logic.
- DIP: Depends on provider interface, not specific SDK.
"""

from typing import Dict, Any
from payments.payment_provider import IPaymentProvider

class PaymentService:
    """
    Abstract payment orchestrator that supports multiple providers.
    """

    def __init__(self, provider: IPaymentProvider):
        self.provider = provider

    def process_payment(self, payment_data: Dict[str, Any], amount: float) -> Dict[str, Any]:
        """
        Processes a payment request through the selected provider.
        """
        return self.provider.create_payment(amount, payment_data)
