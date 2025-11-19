"""
transaction_repository.py
-------------------------
Handles all financial transaction persistence.
"""

from typing import Dict, Any

from ..models.models import Transaction
from ..interfaces.base_repository import BaseRepository


class TransactionRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "transactions", Transaction)

    def get_user_transactions(self, user_id: str):
        return self.list(filters={"user_id": user_id})

    def create_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        txn = Transaction(**data)
        return self.create(txn.to_dict())
