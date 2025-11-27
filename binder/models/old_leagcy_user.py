"""
old_leagcy_user.py
----------------    
this module defines the LegacyUser dataclass for representing
the old Firebase user structure. It includes methods to sanitize

We dont use this module any more but kept for reference
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


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
    first: List[str] = field(default_factory=list)
    msg: Dict[str, Any] = field(default_factory=dict)
    patients: List[Dict[str, Any]] = field(default_factory=list)
    payed: Any = 0
    plan: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_user(self) -> Dict[str, Any]:
        """
        Convert legacy structure to modern User-compatible dict.
        """
        return {
            "id": self.google_id,
            "name": self.name or self.google_id,
            "created_at": self.first or datetime.now().isoformat(),
            "email": None,
            "metadata": {
                "provider":"google",
                "legacy": True,
                "plan": self.plan,
                "settings": self.settings,
                "msg":self.msg,
                "phone": self.phone,
            },
            "clients": self.patients,
            "employees": [],
            "products": [],
            "services": [],
        }







