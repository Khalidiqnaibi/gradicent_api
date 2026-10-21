"""
supabase_file_adapter.py
------------------------
File storage on Supabase: binaries in a PRIVATE Storage bucket, metadata in a Postgres table.

Nothing is ever exposed through a public URL. The browser uploads straight to the bucket with a
one-time signed upload URL, and reads files through signed URLs that expire after a few minutes.
Every metadata query is scoped to the owner (user_id) and workspace (domain).

See documentation/migrations/2026-10-21_private_file_storage.sql for the bucket, columns and policies.
"""


import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from supabase import create_client, Client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseFileStorageAdapter:
    def __init__(self, url: str = "", key: str = ""):
        self.supabase: Client = create_client(url, key)

        # Obfuscated table and bucket names
        self.file_table = os.getenv("DB_TABLE_FILES", "file_metadata_v1")
        self.bucket_name = os.getenv("STORAGE_BUCKET_FILES", "user_assets_v1")

    @property
    def _bucket(self):
        return self.supabase.storage.from_(self.bucket_name)

    # ---------- Storage ----------

    def create_upload_url(self, storage_path: str) -> Dict[str, str]:
        """One-time URL the browser PUTs the file to. Never overwrites an existing object."""
        signed = self._bucket.create_signed_upload_url(storage_path)
        return {"upload_url": signed["signed_url"], "token": signed["token"], "path": storage_path}

    def object_info(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """Size/type of an uploaded object, or None when nothing was uploaded at that path."""
        try:
            info = self._bucket.info(storage_path)
        except Exception:
            return None
        return info if isinstance(info, dict) and (info.get("id") or info.get("name")) else None

    def signed_url(self, storage_path: str, expires_in: int, download_name: Optional[str] = None) -> str:
        options = {"download": download_name} if download_name else None
        res = self._bucket.create_signed_url(storage_path, expires_in, options)
        url = res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
        if not url:
            raise RuntimeError("Storage did not return a signed URL")
        return url

    # ---------- Metadata ----------

    def record_file(self, record: Dict[str, Any]) -> Dict[str, Any]:
        row = {"is_deleted": False, "created_at": _now_iso(), **record}
        res = self.supabase.table(self.file_table).insert(row).execute()
        return res.data[0] if res.data else row

    def find_by_path(self, storage_path: str) -> Optional[Dict[str, Any]]:
        res = self.supabase.table(self.file_table).select("*").eq("url_path", storage_path).limit(1).execute()
        return res.data[0] if res.data else None

    def get_file(self, *, file_id: str, user_id: str, domain: str) -> Optional[Dict[str, Any]]:
        res = self.supabase.table(self.file_table).select("*") \
            .eq("id", file_id) \
            .eq("user_id", user_id) \
            .eq("domain", domain) \
            .eq("is_deleted", False) \
            .limit(1).execute()
        return res.data[0] if res.data else None

    def list_files(self, *, user_id: str, domain: str, client_no: str, folder: Optional[str] = None) -> List[Dict]:
        # Pushes all filtering to the database
        query = self.supabase.table(self.file_table).select("*") \
            .eq("client_no", client_no) \
            .eq("user_id", user_id) \
            .eq("domain", domain) \
            .eq("is_deleted", False)

        if folder:
            query = query.eq("folder", folder)

        response = query.order("created_at", desc=True).execute()
        return response.data

    def soft_delete(self, *, file_id: str, user_id: str, domain: str) -> bool:
        # The binary stays in the private bucket (records are kept), but no URL is ever issued for it again
        response = self.supabase.table(self.file_table).update({
            "is_deleted": True,
            "deleted_at": _now_iso(),
        }).eq("id", file_id).eq("user_id", user_id).eq("domain", domain).eq("is_deleted", False).execute()

        return len(response.data) > 0

    def migrate_legacy_file(self, legacy_file: Dict) -> Dict:
        """
        Takes a dict from your old Firebase 'files' collection
        and inserts it into the new SQL metadata table.
        """
        new_record = {
            "name": legacy_file.get("name"),
            "url_path": legacy_file.get("data"), # The old public URL
            "content_type": legacy_file.get("file_type"),
            "user_id": legacy_file.get("user_id") or legacy_file.get("gid"),
            "client_no": legacy_file.get("client_no") or legacy_file.get("patient_no"),
            "folder": legacy_file.get("folder", "migrated"),
            "is_deleted": False,
            "created_at": legacy_file.get("upload_date", _now_iso())
        }

        self.supabase.table(self.file_table).insert(new_record).execute()
        return new_record
