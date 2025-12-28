from binder import User,normalize_user,normalize_legacy_file
from typing import Dict,Any,Union
from logging import log
import sys


def _provision_user(adapter,legacy_adapter,file_adapter,domain:str, provider: str, provider_user: Dict[str, Any]) -> User:
    provider_id = str(provider_user.get("id"))
    user_id = f"{provider_id}"

    # Try existing user
    raw = adapter.get_user(domain,user_id)
    if raw:
        normalized =  normalize_user(raw)
        if normalized:
            return normalized
        
        # Unknown structure (fallback safe)
        return User(
            id=user_id,
            name=raw.get("name", user_id),
                email=None,
        )
    
    legacy = None
    if domain == "mediacl":
        legacy , legacy_files = get_legacy_user(legacy_adapter,file_adapter,str(provider_user.get('id')))

    if legacy:
        '''
        see if there is an old account 
        and making a new account with the prev data
        but with the new format and path
        '''
        if len(legacy_files) > 0:
            for file in legacy_files:
                file_adapter.migrate_legacy_file(file)

        new_user = normalize_user(legacy.to_dict())
        new_user.metadata["provider"] = provider

        adapter.add_user(domain,user_id, new_user.to_dict())
        return new_user

    
    # Creating new User instance using our model
    new_user = User(
        id=user_id,
        name=provider_user.get("name")
        or provider_user.get("email")
        or user_id,
        email=provider_user.get("email"),
        metadata={
            "provider": provider,
            "provider_id": provider_id,
            "raw": provider_user.get("raw", {}),
            "appointments": []
        },
        clients=[],
        employees=[],
        products=[],
        services=[],
    )

    adapter.add_user(domain,user_id, new_user.to_dict())
    return new_user

def get_legacy_user(adapter, file_adapter, user_id: str):
    """
    Fetch a legacy user, normalize it, and attach normalized legacy files.
    
    Parameters:
    - adapter: the user adapter with get_user(user_id) method
    - file_adapter: FirebaseFileStorageAdapter instance
    - user_id: string ID of the user
    
    Returns:
    - normalized User object with clients
    """
    # print(user_id, file=sys.stderr, flush=True)

    # Fetch raw user data
    raw = adapter.get_user(user_id)
    if not raw:
        return None  # no user found

    # Normalize the user
    normalized = normalize_user(raw)
    if not normalized:
        # fallback safe user
        return User(
            id=user_id,
            name=raw.get("name", user_id),
            email=None,
        )
    
    legacy_files = file_adapter.list_legacy_files(user_id=user_id)
    files = []
    if legacy_files :
        for lf in legacy_files:
            patient_no = lf.get("patient_no")
            if int(patient_no) >= len(normalized.clients):
                continue  

            client = normalized.clients[int(patient_no)]
            if client is None:
                continue

            # normalize file dict
            normalized_file = normalize_legacy_file(lf, client_no=patient_no)
            files.append(normalized_file)
            
        

    return normalized , files


if __name__ ==  "__main__":
    
    user = _provision_user("adapter","provider", "provider_user")