"""
Import the old Firebase data into the Supabase schema used by the API.

  python -I import_legacy.py RTDB_EXPORT.json FILES_BACKUP.json            # dry run: plan + report only
  python -I import_legacy.py RTDB_EXPORT.json FILES_BACKUP.json --apply    # write records
  ... --apply --files                                                      # also copy files (needs GOOGLE_APPLICATION_CREDENTIALS)

Env: SUPABASE_URL, SUPABASE_KEY.

Safe to re-run: every imported row carries record_data.legacy_import = {source, old_id, ...}; rows already
imported are skipped. Existing rows are never modified. Old 0-based record ids become id + 1 (the number
the old app displayed); Firebase push-key ids get the next numbers in creation order. If a number is
already taken in Supabase the record gets the next free number instead (reported).
"""

import datetime as dt
import json
import mimetypes
import os
import re
import sys
import uuid
from collections import Counter, defaultdict

from supabase import create_client

# Same table settings the API reads (DB_TABLE_*), defaulting to the live project's names
T_USERS = os.getenv("DB_TABLE_USERS", "user_accounts_v1")
T_CLIENTS = os.getenv("DB_TABLE_CLIENTS", "crm_entities_v1")
T_LOG = os.getenv("DB_TABLE_INTERACTIONS", "logs_v1")
T_LEDGER = os.getenv("DB_TABLE_TRANSACTIONS", "ledgers_v1")
T_EMP = os.getenv("DB_TABLE_EMPLOYEES", "hr_entities_v1")
T_PROD = os.getenv("DB_TABLE_PRODUCTS", "product_items_v1")
T_SERV = os.getenv("DB_TABLE_SERVICES", "service_catalog_v1")
T_FILES = os.getenv("DB_TABLE_FILES", "file_metadata_v1")
BUCKET = os.getenv("STORAGE_BUCKET_FILES", "user_assets_v1")
SOURCE = "firebase_rtdb"
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
MAX_FILE = 50 * 1024 * 1024
ALLOWED_FILE_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif",
    "image/tiff", "image/bmp", "application/dicom", "text/plain", "text/csv", "application/rtf",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.spreadsheet",
    "audio/mpeg", "audio/mp4", "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/aac",
    "video/mp4", "video/quicktime", "video/webm", "video/x-msvideo", "video/mpeg",
}
FOLDER_CATEGORY = {"medical": {"lab": "lab_results"}, "business": {}}


def items(c):
    """(old_key, record) pairs from an RTDB list (sparse) or dict."""
    if isinstance(c, list):
        return [(str(i), x) for i, x in enumerate(c) if isinstance(x, dict)]
    if isinstance(c, dict):
        return [(str(k), x) for k, x in c.items() if isinstance(x, dict)]
    return []


def visit_items(c):
    """Visits are normally a list/dict of visit objects; some old records hold one visit stored flat."""
    if isinstance(c, dict) and c and not any(isinstance(x, dict) for x in c.values()):
        return [("0", c)] if any(x not in (None, "") for x in c.values()) else []
    return items(c)


def digits(s):
    return re.sub(r"\D", "", str(s or ""))


def norm_gov_id(s):
    return re.sub(r"[\s\-]", "", str(s or "")).upper()


def valid_date(s):
    s = str(s or "")[:10]
    try:
        dt.date.fromisoformat(s)
        return s
    except ValueError:
        return None


def alias(rec, target, *sources):
    """Add a standard field name next to the old one (old fields are kept)."""
    if rec.get(target) not in (None, ""):
        return
    for src in sources:
        if rec.get(src) not in (None, ""):
            rec[target] = rec[src]
            return


def old_ref(c, key):
    """The id other records (files) used for this client: its `id` field, else its key."""
    v = c.get("id")
    return str(v) if v not in (None, "") else key


def number_plan(refs, taken):
    """Map old refs -> new record numbers: digits become n + 1, others follow in key order."""
    plan, conflicts = {}, []
    used = set(taken)
    for ref in sorted((r for r in refs if r.isdigit()), key=int):
        want = int(ref) + 1
        n = want
        while str(n) in used:
            n += 1
        if n != want:
            conflicts.append((ref, want, n))
        plan[ref] = str(n)
        used.add(str(n))
    nxt = max([int(u) for u in used if u.isdigit()] or [0]) + 1
    for ref in sorted(r for r in refs if not r.isdigit()):
        while str(nxt) in used:
            nxt += 1
        plan[ref] = str(nxt)
        used.add(str(nxt))
        nxt += 1
    return plan, conflicts


class Supa:
    def __init__(self):
        self.db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    def select_all(self, table, cols, **eq):
        rows, start = [], 0
        while True:
            q = self.db.table(table).select(cols)
            for k, v in eq.items():
                q = q.eq(k, v)
            batch = q.range(start, start + 999).execute().data or []
            rows.extend(batch)
            if len(batch) < 1000:
                return rows
            start += 1000

    def insert(self, table, rows):
        for i in range(0, len(rows), 500):
            self.db.table(table).insert(rows[i:i + 500]).execute()


def main():
    rtdb_path, files_path = sys.argv[1], sys.argv[2]
    apply = "--apply" in sys.argv
    copy_files = "--files" in sys.argv
    data = json.load(open(rtdb_path, encoding="utf-8"))
    file_rows = json.load(open(files_path, encoding="utf-8"))
    db = Supa()
    report = Counter()
    notes = []
    inserts = defaultdict(list)           # table -> rows
    client_map = {}                        # (domain, owner, old_ref) -> new id

    for domain, users in data.items():
        if domain not in ("medical", "business"):
            notes.append(f"skipped unknown workspace {domain!r}")
            continue
        for owner, u in users.items():
            owner = str(u.get("id") or owner)

            # ---- user row: only created when missing; sign-in keeps an existing row
            if not db.select_all(T_USERS, "id", id=owner, domain=domain):
                meta = {k: v for k, v in (u.get("metadata") or {}).items() if k != "refresh_token"}
                inserts[T_USERS].append({"id": owner, "domain": domain, "record_data": {
                    "id": owner, "name": u.get("name") or owner, "email": u.get("email"),
                    "created_at": u.get("created_at") or NOW, "metadata": meta,
                    "clients": [], "employees": [], "products": [], "services": [],
                }})
                report[f"{domain} users"] += 1

            # ---- clients and their visits / transactions
            existing = db.select_all(T_CLIENTS, "id,legacy:record_data->legacy_import", domain=domain, owner_id=owner)
            taken = {str(r["id"]) for r in existing}
            done = {str((r.get("legacy") or {}).get("old_id")): str(r["id"])
                    for r in existing if (r.get("legacy") or {}).get("source") == SOURCE}
            clients = items(u.get("clients"))
            todo = [(k, c) for k, c in clients if old_ref(c, k) not in done]
            plan, conflicts = number_plan([old_ref(c, k) for k, c in todo], taken)
            for ref, want, got in conflicts:
                notes.append(f"{domain} …{owner[-4:]}: old #{int(ref) + 1} is taken, imported as #{got}")
            for ref, new in done.items():
                client_map[(domain, owner, ref)] = new
            report[f"{domain} clients already imported"] += len(done)

            log_taken = {str(r["id"]) for r in db.select_all(T_LOG, "id", domain=domain, owner_id=owner)}
            ledger_taken = {str(r["id"]) for r in db.select_all(T_LEDGER, "id", domain=domain, owner_id=owner)}
            next_log = max([int(i) for i in log_taken if i.isdigit()] or [0]) + 1
            next_ledger = max([int(i) for i in ledger_taken if i.isdigit()] or [0]) + 1

            for key, c in todo:
                ref = old_ref(c, key)
                if str(c.get("name") or "").startswith("data:"):
                    # Not a real record: an image pasted into every field. It stays in the backup file.
                    notes.append(f"{domain} …{owner[-4:]}: skipped old record {ref} (image data pasted into its fields)")
                    report[f"{domain} clients skipped: not a real record"] += 1
                    continue
                new_id = plan[ref]
                client_map[(domain, owner, ref)] = new_id
                rec = {k: v for k, v in c.items() if k not in ("id", "interactions", "transactions")}
                if not rec.get("created_at"):
                    rec.pop("created_at", None)
                alias(rec, "address", "location")
                if domain == "medical":
                    alias(rec, "phone", "contact")
                    alias(rec, "medical_history", "pmh")
                    alias(rec, "blood_type", "btype")
                    alias(rec, "gender", "sex")
                if rec.get("phone"):
                    rec["phone"] = digits(rec["phone"])     # same normalisation the app applies on save
                if rec.get("gov_id"):
                    rec["gov_id"] = norm_gov_id(rec["gov_id"])

                visits = visit_items(c.get("interactions"))
                dates = [d for d in (valid_date(v.get("visit_date") or v.get("date")) for _, v in visits) if d]
                if visits:
                    rec["total_visits"] = len(visits)
                if dates:
                    rec["last_visit"] = max(d for d in dates if d <= NOW[:10]) if any(d <= NOW[:10] for d in dates) else max(dates)
                rec["legacy_import"] = {"source": SOURCE, "old_id": ref, "imported_at": NOW}
                inserts[T_CLIENTS].append({"id": new_id, "domain": domain, "owner_id": owner, "record_data": rec})
                report[f"{domain} clients"] += 1

                for vkey, v in visits:
                    vrec = dict(v)
                    alias(vrec, "date", "visit_date")
                    alias(vrec, "doctor", "drname")
                    alias(vrec, "weight", "wight")
                    alias(vrec, "cost", "coast")
                    alias(vrec, "paid", "payed")  # (`details` is read as the notes; not copied, it can be long)
                    vrec["legacy_import"] = {"source": SOURCE, "old_client": ref, "old_id": vkey, "imported_at": NOW}
                    while str(next_log) in log_taken:
                        next_log += 1
                    inserts[T_LOG].append({"id": str(next_log), "domain": domain, "owner_id": owner,
                                           "parent_id": new_id, "record_data": vrec})
                    log_taken.add(str(next_log))
                    report[f"{domain} visits/interactions"] += 1
                for tkey, t in items(c.get("transactions")):
                    trec = {k: v for k, v in t.items() if k != "id"}
                    trec["legacy_import"] = {"source": SOURCE, "old_client": ref, "old_id": str(t.get("id") or tkey), "imported_at": NOW}
                    while str(next_ledger) in ledger_taken:
                        next_ledger += 1
                    inserts[T_LEDGER].append({"id": str(next_ledger), "domain": domain, "owner_id": owner,
                                              "parent_id": new_id, "record_data": trec})
                    ledger_taken.add(str(next_ledger))
                    report[f"{domain} transactions"] += 1

            # ---- business catalogue
            for coll, table in (("employees", T_EMP), ("products", T_PROD), ("services", T_SERV)):
                rows = items(u.get(coll))
                if not rows:
                    continue
                ex = db.select_all(table, "id,legacy:record_data->legacy_import", domain=domain, owner_id=owner)
                seen = {str((r.get("legacy") or {}).get("old_id")) for r in ex if (r.get("legacy") or {}).get("source") == SOURCE}
                fresh = [(k, r) for k, r in rows if old_ref(r, k) not in seen]
                cplan, _ = number_plan([old_ref(r, k) for k, r in fresh], {str(r["id"]) for r in ex})
                for k, r in fresh:
                    rec = {kk: vv for kk, vv in r.items() if kk != "id"}
                    rec["legacy_import"] = {"source": SOURCE, "old_id": old_ref(r, k), "imported_at": NOW}
                    inserts[table].append({"id": cplan[old_ref(r, k)], "domain": domain, "owner_id": owner, "record_data": rec})
                    report[f"{domain} {coll}"] += 1

    # ---- files: which workspace/client each one belongs to
    file_plan = []
    owners_by_domain = {d: {str(u.get("id") or k) for k, u in us.items()} for d, us in data.items()}
    for r in file_rows:
        url, owner, ref = str(r.get("data") or ""), str(r.get("user_id")), str(r.get("client_no"))
        if r.get("deleted"):
            report["files skipped: deleted"] += 1
            continue
        if not url.startswith("https://storage.googleapis.com/"):
            report["files skipped: no stored file"] += 1
            continue
        cands = [d for d in ("medical", "business") if (d, owner, ref) in client_map]
        if len(cands) > 1:
            cands = ["medical"] if r.get("folder") in ("drs", "lab") else ["business"]
        if not cands:
            report["files skipped: client not found"] += 1
            continue
        domain = cands[0]
        ctype = (r.get("file_type") or mimetypes.guess_type(r.get("name") or "")[0] or "").lower()
        if ctype not in ALLOWED_FILE_TYPES:
            report[f"files skipped: type {ctype or 'unknown'}"] += 1
            continue
        file_plan.append({"src": url, "owner": owner, "domain": domain, "client": client_map[(domain, owner, ref)],
                          "name": r.get("name") or "file", "type": ctype, "folder": r.get("folder"), "old": r.get("id"),
                          "uploaded": r.get("upload_date")})
    report["files to copy"] = len(file_plan)

    print("PLAN" if not apply else "APPLYING")
    for k in sorted(report):
        print(f"  {k}: {report[k]}")
    for n in notes:
        print("  note:", n)
    if not apply:
        return

    for table in (T_USERS, T_CLIENTS, T_LOG, T_LEDGER, T_EMP, T_PROD, T_SERV):
        if inserts[table]:
            db.insert(table, inserts[table])
            print(f"  inserted {len(inserts[table])} into {table}")

    if copy_files:
        copy_all_files(db, file_plan)


def copy_all_files(db, file_plan):
    import urllib.parse
    import firebase_admin
    from firebase_admin import storage
    firebase_admin.initialize_app(options={"projectId": "monydb-f2cdb", "storageBucket": "monydb-f2cdb.appspot.com"})
    src_bucket = storage.bucket()
    done = {str((r.get("meta") or {}).get("old_file_id")) for r in
            db.select_all(T_FILES, "meta:metadata_payload")
            if (r.get("meta") or {}).get("source") == SOURCE}
    copied = skipped = failed = 0
    for f in file_plan:
        if str(f["old"]) in done:
            skipped += 1
            continue
        try:
            path = urllib.parse.unquote(f["src"].split("/", 4)[4].split("?")[0])
            blob = src_bucket.blob(path)
            body = blob.download_as_bytes()
            if len(body) > MAX_FILE:
                print(f"  too large, left in Firebase: {f['old']} ({len(body) // 1_000_000} MB)")
                failed += 1
                continue
            ext = os.path.splitext(f["name"])[1].lower() or (mimetypes.guess_extension(f["type"]) or "")
            dest = f"{f['domain']}/{f['owner']}/{f['client']}/{uuid.uuid4().hex}{ext}"
            db.db.storage.from_(BUCKET).upload(dest, body, {"content-type": f["type"], "upsert": "false"})
            category = FOLDER_CATEGORY[f["domain"]].get(f["folder"], "other")
            db.db.table(T_FILES).insert({
                "name": f["name"], "url_path": dest, "storage_path": dest, "content_type": f["type"],
                "size_bytes": len(body), "user_id": f["owner"], "domain": f["domain"], "client_no": f["client"],
                "folder": category, "is_deleted": False,
                "created_at": f["uploaded"] or NOW,
                "metadata_payload": {"source": SOURCE, "old_file_id": f["old"], "old_folder": f["folder"]},
            }).execute()
            copied += 1
        except Exception as exc:  # keep going; failures are listed and can be retried by re-running
            failed += 1
            print(f"  failed {f['old']}: {str(exc)[:160]}")
    print(f"  files copied {copied}, already there {skipped}, failed {failed}")


if __name__ == "__main__":
    main()
