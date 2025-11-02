'''
stripe_provider.py
----------------
Stripe payment provider implementation.
'''

from .payment_provider import IPaymentProvider
from typing import Dict

class StripePaymentProvider(IPaymentProvider):
    """
    Stripe payment provider implementation.
    
    Expects:
    - create_payment(amount: float, currency: str, metadata: Dict) -> Dict
    - verify_payment(payload: Dict) -> bool
    
    """

    def create_payment(self, amount: float, currency: str, metadata: Dict) -> Dict:
        # Implement Stripe payment creation logic
        pass

    def verify_payment(self, payload: Dict) -> bool:
        # Implement Stripe payment verification logic
        pass
