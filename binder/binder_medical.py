"""
medical_binder.py
-----------------
Implements user (doctor), client (patient), and interaction (visit)
CRUD operations for the medical domain, using Firebase or similar adapters.
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from .interfaces.binder_mixins import UserMixin, ClientMixin, InteractionMixin
from .interfaces.binder import Binder
from .interfaces.binder_appointment import AppointmentMixin
from .interfaces.permission_code_mixin import PermissionCodeMixin


class BinderMedical(
    Binder, 
    UserMixin, 
    ClientMixin, 
    InteractionMixin,
    AppointmentMixin,
    PermissionCodeMixin
    ):
    """Medical domain binder."""
    
    def __init__(self, adapter, domain = "medical"):
        super().__init__(domain, adapter)
