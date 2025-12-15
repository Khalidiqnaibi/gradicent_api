"""
utils.py
--------
Utility functions for time parsing and validation.
"""

from datetime import datetime
from typing import Optional, List, Dict

DOMAIN_ENTITY_MAP = {
    "medical": "patients",
    "business": "clients",
    "sales": "customers",
}

def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse string or timestamp into datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def _match_visit(
    visits: List[Dict],
    *,
    details=None,
    start_date=None,
    end_date=None,
    visit_filters=None
):
    """Efficient visit filtering with early exit."""
    for v in visits:

        # ---- details filter ----
        if details and details not in v.get("_details_lc", ""):
            continue

        # ---- dynamic visit filters (treatment, lab, service, product, etc.) ----
        if visit_filters:
            ok = True
            for key, value in visit_filters.items():
                if value and value not in v.get(key, ""):
                    ok = False
                    break
            if not ok:
                continue

        # ---- date filter ----
        if start_date or end_date:
            vd = v.get("_vd")
            if not vd:
                continue
            if (start_date and vd < start_date) or (end_date and vd > end_date):
                continue

        # if ANY visit matches → patient matches
        return True

    return False

def filter_patients(patients: List[Dict], f: Dict):
    # Extract filters
    details = (f.get("details", "") or "").lower()
    location = (f.get("location", "") or "").lower()
    treatment = (f.get("treatment", "") or "").lower()
    diagnosis = (f.get("diagnosis", "") or "").lower()
    lab = (f.get("lab", "") or "").lower()

    start_raw = f.get("start_date") or f.get("from") or f.get("From")
    end_raw   = f.get("end_date") or f.get("to") or f.get("To")

    start_date = parse_date(start_raw)
    end_date   = parse_date(end_raw)

    # visits filter dict
    visit_filters = {
        "treatment": treatment,
        "diagnosis": diagnosis,
        "lab": lab
    }

    if not start_date and not end_date and treatment == '' and diagnosis == '' and lab == '':
        return patients
    matched = []
    append = matched.append   # local binding (micro-optim)

    # Precompute lowercase once
    for p in patients:
        # ---- patient-level filters ----
        if location and location != p.get("location", "").lower():
            continue

        visits = p.get("visits", [])
        if not visits:
            continue
        
        if (not type(visits) is list):
            visits = [visits]

        # Precompute lowercase and parsed dates ONCE
        for v in visits:
            if "_details_lc" not in v:
                v["_details_lc"] = v.get("details", "").lower()
            if "_vd" not in v:
                v["_vd"] = parse_date(v.get("visit_date"))

        # ---- match visits ----
        if _match_visit(
            visits,
            details=details,
            start_date=start_date,
            end_date=end_date,
            visit_filters=visit_filters
        ):
            append(p)

    return matched

def filter_clients(clients: List[Dict], f: Dict):

    details = (f.get("details", "") or "").lower()
    location = (f.get("location", "") or "").lower()
    service = (f.get("service", "") or "").lower()
    product = (f.get("product", "") or "").lower()

    start_raw = f.get("start_date") or f.get("from") or f.get("From")
    end_raw   = f.get("end_date") or f.get("to") or f.get("To")

    start_date = parse_date(start_raw)
    end_date   = parse_date(end_raw)

    visit_filters = {
        "service": service,
        "product": product
    }

    
    if not start_date and not end_date and service == '' and product == '':
        return clients

    matched = []
    append = matched.append

    for p in clients:

        # patient-level filters
        if location and location != p.get("location", "").lower():
            continue

        visits = p.get("visits", [])
        if not visits:
            continue

        # preprocess visit data
        print(list(visits))
        for v in list(visits):
            if "_details_lc" not in v:
                v["_details_lc"] = v.get("details", "").lower()
            if "_vd" not in v:
                v["_vd"] = parse_date(v.get("visit_date"))

        if _match_visit(
            visits,
            details=details,
            start_date=start_date,
            end_date=end_date,
            visit_filters=visit_filters
        ):
            append(p)

    return matched
