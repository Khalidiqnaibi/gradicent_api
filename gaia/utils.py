"""
utils.py
--------
Utility functions for time parsing and validation.
"""

from datetime import datetime
from typing import Optional

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

def filter_clients(clients, filters):
    start_date = filters.get("start_date")
    end_date   = filters.get("end_date")
    details    = filters.get("details", "").lower()
    location   = filters.get("location", "").lower()
    service  = filters.get("service", "").lower()
    product  = filters.get("product", "").lower()
    show_date  = filters.get("show_date", False)
    show_visit_info = filters.get("show_visit_info", False)

    if start_date or start_date:
        show_date = True

    if location or service or product:
        show_visit_info = True

    matched = []

    for patient in clients.values():
        # patient-level filters
        if location and patient.get("location", "").lower() != location:
            continue

        visits = patient.get("visits", [])

        if details:
            if not any(details in v.get("details", "").lower() for v in visits):
                continue

        if show_visit_info:
            ok = any(
                (not service or service in v.get("service", "").lower()) and
                (not product or product in v.get("product", "").lower())
                for v in visits
            )
            if not ok:
                continue

        if show_date:
            ok = any(
                (not start_date or not end_date or start_date <= v.get("visit_date", "") <= end_date)
                for v in visits
            )
            if not ok:
                continue

        matched.append(patient)

    return matched

def filter_patients(patients, filters):
    start_date = filters.get("start_date")
    end_date   = filters.get("end_date")
    details    = filters.get("details", "").lower()
    location   = filters.get("location", "").lower()
    treatment  = filters.get("treatment", "").lower()
    diagnosis  = filters.get("diagnosis", "").lower()
    lab        = filters.get("lab", "").lower()
    show_date  = filters.get("show_date", False)
    show_visit_info = filters.get("show_visit_info", False)

    if start_date or start_date:
        show_date = True

    if location or treatment or diagnosis or lab:
        show_visit_info = True

    matched = []

    for patient in patients.values():
        # patient-level filters
        if location and patient.get("location", "").lower() != location:
            continue

        visits = patient.get("visits", [])

        if details:
            if not any(details in v.get("details", "").lower() for v in visits):
                continue

        if show_visit_info:
            ok = any(
                (not treatment or treatment in v.get("treatment", "").lower()) and
                (not diagnosis or diagnosis in v.get("diagnosis", "").lower()) and
                (not lab or lab in v.get("lab", "").lower())
                for v in visits
            )
            if not ok:
                continue

        if show_date:
            ok = any(
                (not start_date or not end_date or start_date <= v.get("visit_date", "") <= end_date)
                for v in visits
            )
            if not ok:
                continue

        matched.append(patient)

    return matched
