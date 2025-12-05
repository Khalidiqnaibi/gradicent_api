
from binder import User,LegacyUser
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