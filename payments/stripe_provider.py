'''
stripe_provider.py
----------------
Stripe payment provider implementation.
'''

from .payment_provider import IPaymentProvider
from typing import Dict ,Any
import stripe

class StripePaymentProvider(IPaymentProvider):
    """
    Stripe payment provider implementation.
    
    Expects:
    - create_payment(amount: float, currency: str, metadata: Dict) -> Dict
    - verify_payment(payload: Dict) -> bool
    
    """
    def __init__(self, api_key: str):
        stripe.api_key = api_key
        self.stripe = stripe

    def create_payment(self, amount: float, metadata: Dict[str, Any],currency: str= "usd") -> Dict[str, Any]:
        try:
            charge = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                payment_method=metadata.get("payment_method_id"),
                confirm=True
            )
            return {"status": "success", "data":{"id": charge.id},
                    "message": f"Payment Created successfully. Amount: {amount}{currency},Id: {charge.id} "}
        except Exception as e:
            return {"status": "error","data":{}, "message": str(e)}

    def verify_payment(self, payload: Dict) -> bool:
        # Implement Stripe payment verification logic
        pass
