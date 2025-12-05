'''
normalize_user.py
--------------------
User normalization utility.
Converts legacy user formats to the new User model.
and ensures consistent structure.

inputs:
- legacy user dict (with google_id or patients) or
- new user dict (with metadata and first)
outputs:
- User model instance or None if unrecognized structure.
'''

from ..models.models import User
from ..models.legacy_user import LegacyUser
from typing import Union

def normalize_user(user) -> Union[User,None]:
    #  NEW FORMAT
    if "metadata" in user and "first" not in user:
        return User(**user)

    #  LEGACY FORMAT
    if "google_id" in user or "patients" in user:
        legacy_user = LegacyUser.from_raw(user)
        converted = legacy_user.to_user()
        return User(**converted)
    
    return None