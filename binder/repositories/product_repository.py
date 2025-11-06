"""
product_repository.py
--------------------
Repository for product data management.
"""

from typing import Dict, Any
from binder import Product,  BaseRepository


class ProductRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "product", Product)

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        product = Product(**data)
        return self.create(product.to_dict())

    def get_products_for_user(self, user_id: str) -> list:
        return self.list(filters={"user_id": user_id})
