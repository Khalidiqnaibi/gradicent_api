"""
Link the old app's files (Firestore "gradicent files") to the records imported into Supabase.

  python -I link_firebase_files.py            # dry run
  python -I link_firebase_files.py --apply    # write

Env: SUPABASE_URL, SUPABASE_KEY, DB_TABLE_CLIENTS (optional), GOOGLE_APPLICATION_CREDENTIALS (Firebase key).

Only ADDS fields to each document (existing fields are never changed):
  domain, client_id (record number in the current app), category, storage_path
Documents already carrying client_id are left alone, so it is safe to re-run.
"""

import os
import sys
import urllib.parse
from collections import Counter

import firebase_admin
from firebase_admin import firestore
from supabase import create_client

COLLECTION = os.getenv("FIREBASE_FILES_COLLECTION", "gradicent files")
T_CLIENTS = os.getenv("DB_TABLE_CLIENTS", "crm_entities_v1")
CATEGORY = {"lab": "lab_results"}


def legacy_map(db):
    """(owner, old_id) -> {domain: record number} from rows the importer tagged with legacy_import."""
    mapping, start = {}, 0
    while True:
        rows = (db.table(T_CLIENTS).select("id,domain,owner_id,legacy:record_data->legacy_import")
                .range(start, start + 999).execute().data or [])
        for r in rows:
            legacy = r.get("legacy") or {}
            if legacy.get("source") == "firebase_rtdb":
                mapping.setdefault((str(r["owner_id"]), str(legacy.get("old_id"))), {})[r["domain"]] = str(r["id"])
        if len(rows) < 1000:
            return mapping
        start += 1000


def storage_path(url: str):
    if not url.startswith("https://storage.googleapis.com/"):
        return None
    return urllib.parse.unquote(url.split("/", 4)[4].split("?")[0])


def main():
    apply = "--apply" in sys.argv
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    mapping = legacy_map(sb)
    firebase_admin.initialize_app(options={"projectId": "monydb-f2cdb"})
    files = firestore.client().collection(COLLECTION)
    report, updates = Counter(), []
    for doc in files.stream():
        d = doc.to_dict() or {}
        if d.get("client_id"):
            report["already linked"] += 1
            continue
        path = storage_path(str(d.get("data") or ""))
        targets = mapping.get((str(d.get("user_id")), str(d.get("client_no"))), {})
        if not path or not targets:
            report["no matching record or file"] += 1
            continue
        domain = next(iter(targets)) if len(targets) == 1 else (
            "medical" if d.get("folder") in ("drs", "lab") else "business")
        updates.append((doc.reference, {
            "domain": domain,
            "client_id": targets[domain],
            "category": CATEGORY.get(d.get("folder"), "other"),
            "storage_path": path,
        }))
        report[f"to link ({domain})"] += 1
    for k in sorted(report):
        print(f"  {k}: {report[k]}")
    if not apply:
        return
    batch, n = firestore.client().batch(), 0
    for ref, fields in updates:
        batch.update(ref, fields)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = firestore.client().batch()
    batch.commit()
    print(f"  linked {n} documents")


if __name__ == "__main__":
    main()
