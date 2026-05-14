from binder import User,normalize_user
from typing import Dict,Any


def _provision_user(adapter,domain:str, provider: str, provider_user: Dict[str, Any]) -> User:
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

if __name__ ==  "__main__":
    
    user = _provision_user("adapter","provider", "provider_user")