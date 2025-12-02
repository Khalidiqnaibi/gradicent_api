"""
leagcy_user.py
----------------    
this module defines the LegacyUser dataclass for representing
the old Firebase user structure. It includes methods to sanitize
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


def sanitize_legacy_data(raw: dict, model) -> dict:
    """
    Keeps only fields that exist in the dataclass model.
    This protects against random legacy fields.
    """
    allowed = model.__dataclass_fields__.keys()
    return {k: v for k, v in raw.items() if k in allowed}


@dataclass
class LegacyUser:
    """
    Represents the old Firebase user structure.
    This class is READ-ONLY. Used only for compatibility.
    """

    google_id: str
    name: Optional[str] = None
    phone: Optional[str] = None

    # legacy fields
    first: str = datetime.now().isoformat()
    msg: Dict[str, Any] = field(default_factory=dict)
    patients: List[Dict[str, Any]] = field(default_factory=list)
    payed: Any = 0
    plan: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str,Any]] = None

    @classmethod
    def from_raw(cls, raw: dict):
        """
        Creates a LegacyUser from raw Firebase data.
        Unknown fields are ignored safely.
        """
        clean = sanitize_legacy_data(raw, cls)
        return cls(**clean)

    def to_user(self) -> Dict[str, Any]:
        """
        Convert legacy structure to modern User-compatible dict.
        """
        return {
            "id": self.google_id,
            "name": self.name or self.google_id,
            "created_at": self.first,
            "email": None,
            "metadata": {
                "provider": "google",
                "legacy": True,
                "plan": self.plan,
                "settings": self.settings,
                "appointments": self.msg,
                "phone": self.phone,
                "legacy metadata": self.metadata,
            },
            "clients": self.patients,
            "employees": [],
            "products": [],
            "services": [],
        }
