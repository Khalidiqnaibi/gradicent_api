"""
Payment service module for handling different payment providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class IPaymentProvider(ABC):
    @abstractmethod
    def create_checkout(self, amount: float, return_url: str, cancel_url: str, **meta) -> Dict[str,str]:
        pass

    @abstractmethod
    def verify_payment(self, payment_id: str, **kwargs) -> bool:
        pass

class PaddleProvider(IPaymentProvider):
    def __init__(self, api_key): ...
    def create_checkout(...): ...
    def verify_payment(...): ...

class PayPalProvider(IPaymentProvider):
    def __init__(self, client_id, secret): ...
    def create_checkout(...): ...
    def verify_payment(...): ...

class PaymentService:
    def __init__(self, providers: Dict[str, IPaymentProvider]):
        self.providers = providers

    def checkout(self, provider_name: str, **kwargs):
        provider = self.providers[provider_name]
        return provider.create_checkout(**kwargs)

    def confirm(self, provider_name: str, payment_id: str, **kwargs) -> bool:
        return self.providers[provider_name].verify_payment(payment_id, **kwargs)
