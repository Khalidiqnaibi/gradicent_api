""" 
normalize_user.py
-------------------
User normalization_user.

Converts legacy and modern user formats into the unified User model.
Ensures:
- deterministic client IDs (positional index)
- gov_id is NOT used as internal ID
- uniform client / interaction structures
- uses FirebaseFileStorageAdapter
- migrates legacy users + clients
- migrates legacy files into new format
"""

from typing import Union, Dict, Any, List
from datetime import datetime

from ..models.models import User
from ..models.legacy_user import LegacyUser

def now_iso() -> str:
    return datetime.now().isoformat()


def s(x) -> str:
    return "" if x is None else str(x)


def i(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def f(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def iso(x) -> str:
    if x is None:
        return ""
    if isinstance(x, datetime):
        return x.isoformat()
    return str(x)


def normalize_sex(x: str ) -> str:
    if not x:
        return None
    x = x.lower().strip()
    if x in ("m", "male"):
        return "male"
    if x in ("f", "female"):
        return "female"
    return x

def get_interaction_per_domain(raw: Dict[str, Any], domain: str) -> Dict[str, Any]:
    return {
        "coast": f(raw.get("coast", raw.get("cost", 0))),
        "debit": f(raw.get("debit", 0)),
        "details": s(raw.get("details", "")),
        "diagnosis": s(raw.get("diagnosis", "")),
        "drname": s(raw.get("drname", "")),
        "height": s(raw.get("height", "0")),
        "lab": raw.get("lab", ""),
        "payed": f(raw.get("payed", 0)),
        "treatment": s(raw.get("treatment", "")),
        "visit_date": iso(raw.get("visit_date", raw.get("date"))),
        "vno": i(raw.get("vno", raw.get("no", 0))),
        "wight": s(raw.get("wight", raw.get("weight", "0"))),
        "printed": bool(raw.get("printed", False)),
        "metadata": raw.get("metadata", {}),
    }

def normalize_interactions(raw: Any , domain:str) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [get_interaction_per_domain(v,domain) for v in raw if isinstance(v, dict)]
    if isinstance(raw, dict):
        return [get_interaction_per_domain(raw,domain)]
    return []

def normalize_client(raw: Dict[str, Any] , domain : str) -> Dict[str, Any]:
    """
    Returns a client dict WITHOUT id.
    id is assigned later based on list index.
    """
    interactions = []

    if "interactions" in raw:
        interactions = normalize_interactions(raw["interactions"])
    elif "visits" in raw:
        interactions = normalize_interactions(raw["visits"])

    client = {
        # id intentionally missing
        "name": s(raw.get("name", "unknown")),
        "contact": s(raw.get("phone", raw.get("contact", ""))),
        "created_at": iso(raw.get("created_at", raw.get("first"))),
        # gov_id is TOP-LEVEL
        "gov_id": s(raw.get("gov_id", raw.get("id"))),
        "legacy_no": raw.get("no"),
        "sex": normalize_sex(raw.get("sex")),
        "age": raw.get("age") ,
        "btype": raw.get("btype"),
        "location": raw.get("location"),
        "pmh": raw.get("pmh"),
        "metadata": {
            # preserve legacy arrays safely
            **({"lab": raw.get("lab")} if raw.get("lab") else {}),
            **({"pharma": raw.get("pharma")} if raw.get("pharma") else {}),
            **({"radio": raw.get("radio")} if raw.get("radio") else {}),
            **({"payload": raw.get("payload")} if raw.get("payload") else {}),
        },
        "interactions": interactions,
        "transactions": [],
    }

    for i in raw.keys():
        if not client.get(i) and not client.get("metadata").get(i):
            client[i]= raw[i]

    return client


def normalize_user(user: Any) -> Union[User, None]:
    if user is None:
        return None

    if isinstance(user, dict) and "metadata" in user and "first" not in user:
        raw_clients = user.get("clients", [])

        clients: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_clients):
            if not isinstance(raw, dict):
                continue
            c = normalize_client(raw)
            c["id"] = str(idx)  #  positional ID
            clients.append(c)

        return User(
            id=s(user.get("id")),
            name=s(user.get("name")),
            email=user.get("email"),
            created_at=iso(user.get("created_at")),
            metadata=user.get("metadata", {}),
            clients=clients,
            employees=user.get("employees", []),
            products=user.get("products", []),
            services=user.get("services", []),
        )

    # LEGACY USER FORMAT
    if isinstance(user, dict) and (
        "google_id" in user or "patients" in user
    ):
        legacy = LegacyUser.from_raw(user)
        base = legacy.to_user()

        raw_clients = base.get("clients", [])

        clients: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_clients):
            if not isinstance(raw, dict):
                continue
            c = normalize_client(raw)
            c["id"] = str(idx)  # positional ID
            clients.append(c)

        return User(
            id=s(base["id"]),
            name=s(base["name"]),
            email=base.get("email"),
            created_at=iso(base.get("created_at")),
            metadata=base.get("metadata", {}),
            clients=clients,
            employees=[],
            products=[],
            services=[],
        )

    return None


def normalize_legacy_file(legacy_file: Dict[str, Any], client_no: str) -> Dict[str, Any]:
    """
    Convert a legacy file dict into the new file format.
    
    Parameters:
    - legacy_file: dict with keys like 'data', 'file_type', 'folder', 'gid', 'name', 'patient_no', 'upload_date'
    - client_no: positional string ID of the client
    
    Returns:
    - dict in new file format
    """
    if not legacy_file:
        return None
    return {
        "name": legacy_file.get("name", "unknown"),
        "data": legacy_file.get("data", ""),
        "file_type": legacy_file.get("file_type", "application/octet-stream"),
        "upload_date": legacy_file.get("upload_date", ""),
        "deleted": False,
        "deleted_at": None,
        "user_id": legacy_file.get("gid", ""),
        "client_no": client_no,
        "folder": legacy_file.get("folder", "misc"),
        "metadata": {
            "legacy": True,
            # preserve original legacy doc id or extras if present
            **({k: legacy_file[k] for k in ("gid", "patient_no") if k in legacy_file}),
        },
    }
