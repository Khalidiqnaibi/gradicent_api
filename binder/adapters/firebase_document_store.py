"""
firebase_document_store.py
--------------------------
Patient / client documents on Firebase: binaries in Firebase (Cloud) Storage, details in the
Firestore "gradicent files" collection (the collection the old app used, so old and new files
live side by side).

Same contract as SupabaseFileStorageAdapter, so FileService works with either:
- browser uploads go straight to the bucket through a one-time V4 signed PUT URL
  (with x-goog-if-generation-match: 0, so an upload can never overwrite an existing object)
- files are read through signed GET URLs that expire after a few minutes; nothing is public
- every query is scoped to the owner (user_id) and workspace (domain)

Firestore fields (old documents keep theirs; documents written here add the newer ones):
  name, file_type, user_id, client_no, folder, upload_date, deleted, deleted_at, data, metadata  (old app)
  domain, client_id, category, storage_path, size_bytes                                          (added)
`client_id` is the record number in the current app; old documents' `client_no` used the old
numbering and is kept as-is.
"""

import datetime as dt
from typing import Any, Dict, List, Optional

from firebase_admin import firestore, storage

SIGNED_UPLOAD_TTL = dt.timedelta(hours=2)
CATEGORY_FROM_OLD_FOLDER = {"lab": "lab_results"}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class FirebaseDocumentStore:
    def __init__(self, app, collection: str = "gradicent files"):
        self._db = firestore.client(app=app)
        self._bucket = storage.bucket(app=app)
        self._files = self._db.collection(collection)

    # ---------- Storage ----------

    def create_upload_url(self, storage_path: str, content_type: str) -> Dict[str, Any]:
        headers = {"Content-Type": content_type, "x-goog-if-generation-match": "0"}
        url = self._bucket.blob(storage_path).generate_signed_url(
            version="v4", expiration=SIGNED_UPLOAD_TTL, method="PUT",
            content_type=content_type, headers={"x-goog-if-generation-match": "0"},
        )
        return {"upload_url": url, "path": storage_path, "headers": headers}

    def object_info(self, storage_path: str) -> Optional[Dict[str, Any]]:
        blob = self._bucket.get_blob(storage_path)
        if blob is None:
            return None
        return {"id": blob.id, "size": blob.size, "content_type": blob.content_type}

    def signed_url(self, storage_path: str, expires_in: int, download_name: Optional[str] = None) -> str:
        kwargs = {}
        if download_name:
            safe = download_name.replace('"', "")
            kwargs["response_disposition"] = f"attachment; filename*=UTF-8''{_quote(safe)}"
        return self._bucket.blob(storage_path).generate_signed_url(
            version="v4", expiration=dt.timedelta(seconds=expires_in), method="GET", **kwargs,
        )

    # ---------- Metadata ----------

    @staticmethod
    def _row(doc) -> Dict[str, Any]:
        """A Firestore document in the row shape FileService expects (same as the Supabase table)."""
        d = doc.to_dict() or {}
        return {
            "id": doc.id,
            "name": d.get("name"),
            "content_type": d.get("file_type") or d.get("content_type"),
            "size_bytes": d.get("size_bytes"),
            "folder": d.get("category") or CATEGORY_FROM_OLD_FOLDER.get(d.get("folder"), "other"),
            "client_no": d.get("client_id"),
            "created_at": d.get("upload_date"),
            "storage_path": d.get("storage_path"),
            "url_path": d.get("storage_path"),
            "user_id": d.get("user_id"),
            "domain": d.get("domain"),
            "is_deleted": bool(d.get("deleted")),
        }

    def record_file(self, record: Dict[str, Any]) -> Dict[str, Any]:
        now = _now_iso()
        doc = {
            "name": record["name"],
            "file_type": record.get("content_type"),
            "size_bytes": record.get("size_bytes"),
            "user_id": record["user_id"],
            "domain": record["domain"],
            "client_id": str(record["client_no"]),
            "client_no": str(record["client_no"]),
            "category": record.get("folder") or "other",
            "folder": record.get("folder") or "other",
            "storage_path": record["storage_path"],
            "data": f"gs://{self._bucket.name}/{record['storage_path']}",
            "upload_date": now,
            "deleted": False,
            "deleted_at": None,
            "metadata": record.get("metadata_payload") or {},
        }
        ref = self._files.document()
        ref.set(doc)
        return self._row(ref.get())

    def find_by_path(self, storage_path: str) -> Optional[Dict[str, Any]]:
        docs = list(self._files.where("storage_path", "==", storage_path).limit(1).stream())
        return self._row(docs[0]) if docs else None

    def get_file(self, *, file_id: str, user_id: str, domain: str) -> Optional[Dict[str, Any]]:
        snap = self._files.document(file_id).get()
        if not snap.exists:
            return None
        row = self._row(snap)
        if row["user_id"] != user_id or row["domain"] != domain or row["is_deleted"] or not row["storage_path"]:
            return None
        return row

    def _owned_docs(self, user_id: str, domain: str, client_no: str):
        return (self._files.where("user_id", "==", user_id).where("domain", "==", domain)
                .where("client_id", "==", str(client_no)).where("deleted", "==", False).stream())

    def list_files(self, *, user_id: str, domain: str, client_no: str, folder: Optional[str] = None) -> List[Dict]:
        rows = [self._row(d) for d in self._owned_docs(user_id, domain, client_no)]
        rows = [r for r in rows if r["storage_path"] and (not folder or r["folder"] == folder)]
        return sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)

    def soft_delete(self, *, file_id: str, user_id: str, domain: str) -> bool:
        if not self.get_file(file_id=file_id, user_id=user_id, domain=domain):
            return False
        # The binary stays in the bucket (records are kept), but no URL is ever issued for it again
        self._files.document(file_id).update({"deleted": True, "deleted_at": _now_iso()})
        return True

    def soft_delete_client_files(self, *, user_id: str, domain: str, client_no: str) -> int:
        count = 0
        for doc in self._owned_docs(user_id, domain, client_no):
            doc.reference.update({"deleted": True, "deleted_at": _now_iso()})
            count += 1
        return count


def _quote(name: str) -> str:
    from urllib.parse import quote
    return quote(name, safe="")
