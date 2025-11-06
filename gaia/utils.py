"""
utils.py
--------
Utility functions for time parsing and validation.
"""

from datetime import datetime
from typing import Optional


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse string or timestamp into datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
