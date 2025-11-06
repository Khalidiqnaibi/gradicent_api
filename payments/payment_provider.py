'''
payment_provider.py 
----------------
Payment provider abstractions.
'''


from abc import ABC, abstractmethod
from typing import Dict

class IPaymentProvider(ABC):
    """Abstract payment provider."""

    @abstractmethod
    def create_payment(self, amount: float, currency: str, metadata: Dict) -> Dict:
        pass

    @abstractmethod
    def verify_payment(self, payload: Dict) -> bool:
        pass
