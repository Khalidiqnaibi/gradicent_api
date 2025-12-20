"""
Binder Business
------------------------------
BinderBusiness: storage-agnostic implementation using StorageAdapter.
All methods return / accept model dicts (uniform schema).
"""

from typing import Any, Dict, Optional , List
from .interfaces.storage_adapter import StorageAdapter
from .interfaces.binder import Binder
from .interfaces.binder_appointment import AppointmentMixin
from .interfaces.permission_code_mixin import PermissionCodeMixin
from .interfaces.binder_mixins import (
    UserMixin,
    ClientMixin,
    EmployeeMixin,
    ProductMixin,
    ServiceMixin,
    InteractionMixin,
    TransactionMixin,
)

class BinderBusiness(
    Binder,
    UserMixin,
    ClientMixin,
    EmployeeMixin,
    ProductMixin,
    ServiceMixin,
    InteractionMixin,
    TransactionMixin,
    AppointmentMixin,
    PermissionCodeMixin
):
    """
    Binder Business that stores and reads uniform model dicts.
    Uses StorageAdapter interface so any DB backend can be plugged.
    """

    def __init__(self, adapter, domain = "business"):
        super().__init__(domain, adapter)