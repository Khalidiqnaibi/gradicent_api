from binder import User,normalize_user
from typing import Dict,Any


def _provision_user(adapter,domain:str, provider: str, provider_user: Dict[str, Any]) -> User:
    provider_id = str(provider_user.get("id"))

    # Try existing user
    raw = adapter.get_user(domain,provider_id)
    if raw: 
        normalized =  normalize_user(raw)
        if normalized:
            return normalized
        
        # Unknown structure (fallback safe)
        return User(
            id=provider_id,
            name=raw.get("name", provider_id),
                email=None,
        )
    
    new_user = User(
        id=provider_id,
        name=provider_user.get("name")
        or provider_user.get("email")
        or provider_id,
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

    adapter.add_user(domain,provider_id, new_user.to_dict())
    return new_user

if __name__ ==  "__main__":
    
    user = _provision_user("adapter","provider", "provider_user")