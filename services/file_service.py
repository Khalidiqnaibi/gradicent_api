"""
file_service.py
---------------
Domain-level file operations: patient/client documents kept in private storage.

Upload flow (the file never passes through the API, so big scans aren't limited by its body size):
    1. prepare_upload()  -> validates name/type/size, returns a one-time signed upload URL
    2. browser PUTs the file to that URL
    3. register_upload() -> checks the object really landed in the caller's folder, stores metadata
Reads go through signed_url(), which expires after a few minutes.
"""

import os
import re
import uuid
import unicodedata
from typing import Any, Dict, List, Optional


class FileServiceError(Exception):
    """A request we can't honour; the message is safe to show to the user."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


MAX_FILE_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
SIGNED_URL_TTL_SECONDS = 300

# extension -> canonical content type. Keep in step with the bucket's allowed_mime_types.
ALLOWED_TYPES: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
    ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
    ".tif": "image/tiff", ".tiff": "image/tiff", ".bmp": "image/bmp",
    ".dcm": "application/dicom",
    ".txt": "text/plain", ".csv": "text/csv", ".rtf": "application/rtf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg", ".aac": "audio/aac",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".avi": "video/x-msvideo",
    ".mpeg": "video/mpeg", ".mpg": "video/mpeg",
}
ALLOWED_MIME_TYPES = set(ALLOWED_TYPES.values()) | {"audio/x-wav", "audio/webm"}

CATEGORIES = {
    "medical": ("lab_results", "imaging", "prescriptions", "referrals", "consent_forms", "insurance", "other"),
    "business": ("contracts", "invoices", "receipts", "identification", "correspondence", "other"),
}

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def clean_display_name(name: str) -> str:
    """Keep the user's file name (any language) but drop path parts and control characters."""
    name = unicodedata.normalize("NFC", str(name or "")).replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip(" .")
    return name[:200]


def _extension(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def public_file(row: Dict[str, Any]) -> Dict[str, Any]:
    """What the browser gets: never the storage path or owner id."""
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "content_type": row.get("content_type"),
        "size": row.get("size_bytes"),
        "category": row.get("folder") or "other",
        "client_id": row.get("client_no"),
        "created_at": row.get("created_at"),
    }


class FileService:
    '''
    service for file operations
    that uses a storage adapter (SupabaseFileStorageAdapter)
    and provides domain logic: validation, owner/workspace scoping and storage layout.

    Storage layout: <domain>/<user_id>/<client_id>/<random>.<ext>
    Object names carry no patient/client information; the readable name lives in the metadata row.
    '''
    def __init__(self, storage_adapter):
        self.storage = storage_adapter

    # ---------- validation ----------

    @staticmethod
    def _check_scope(domain: str, client_id: str) -> None:
        if domain not in CATEGORIES:
            raise FileServiceError("Unknown workspace.")
        if not _SAFE_ID.match(str(client_id or "")):
            raise FileServiceError("A valid client or patient is required.")

    @staticmethod
    def _category(domain: str, category: Optional[str]) -> str:
        category = (category or "other").strip().lower()
        if category not in CATEGORIES[domain]:
            raise FileServiceError("Unknown document category.")
        return category

    @staticmethod
    def _content_type(name: str, content_type: Optional[str]) -> str:
        ext = _extension(name)
        if ext not in ALLOWED_TYPES:
            raise FileServiceError(
                "This file type isn't supported. Upload a PDF, image, Office document, audio or video file.", 415
            )
        content_type = (content_type or "").split(";")[0].strip().lower()
        # Browsers send an empty or generic type for e.g. .heic and .dcm; fall back to the extension
        return content_type if content_type in ALLOWED_MIME_TYPES else ALLOWED_TYPES[ext]

    @staticmethod
    def _folder_prefix(domain: str, user_id: str, client_id: str) -> str:
        return f"{domain}/{user_id}/{client_id}/"

    # ---------- operations ----------

    def prepare_upload(
        self, *, domain: str, user_id: str, client_id: str, name: str, content_type: Optional[str], size: Any,
    ) -> Dict[str, Any]:
        self._check_scope(domain, client_id)
        display_name = clean_display_name(name)
        if not display_name:
            raise FileServiceError("The file needs a name.")
        resolved_type = self._content_type(display_name, content_type)
        try:
            size = int(size)
        except (TypeError, ValueError):
            raise FileServiceError("File size is missing.")
        if size <= 0:
            raise FileServiceError("The file is empty.")
        if size > MAX_FILE_BYTES:
            raise FileServiceError(f"Files can be at most {MAX_FILE_BYTES // (1024 * 1024)} MB.", 413)

        path = f"{self._folder_prefix(domain, user_id, client_id)}{uuid.uuid4().hex}{_extension(display_name)}"
        signed = self.storage.create_upload_url(path)
        return {
            "upload_url": signed["upload_url"],
            "path": path,
            "content_type": resolved_type,
            "max_bytes": MAX_FILE_BYTES,
        }

    def register_upload(
        self, *, domain: str, user_id: str, client_id: str, path: str, name: str, category: Optional[str],
    ) -> Dict[str, Any]:
        self._check_scope(domain, client_id)
        category = self._category(domain, category)
        display_name = clean_display_name(name)
        path = str(path or "")
        # Only objects inside the caller's own folder for this client can be attached
        if (not path.startswith(self._folder_prefix(domain, user_id, client_id))
                or ".." in path or not display_name):
            raise FileServiceError("Invalid upload.", 403)
        if self.storage.find_by_path(path):
            raise FileServiceError("This upload was already saved.", 409)
        info = self.storage.object_info(path)
        if not info:
            raise FileServiceError("The upload didn't finish. Please try again.", 409)

        meta = info.get("metadata") if isinstance(info.get("metadata"), dict) else {}
        size = info.get("size") or meta.get("size") or meta.get("contentLength")
        stored_type = info.get("content_type") or info.get("contentType") or meta.get("mimetype")
        row = self.storage.record_file({
            "name": display_name,
            "url_path": path,
            "storage_path": path,
            "content_type": stored_type or self._content_type(display_name, None),
            "size_bytes": int(size) if str(size or "").isdigit() else None,
            "user_id": user_id,
            "domain": domain,
            "client_no": str(client_id),
            "folder": category,
            "metadata_payload": {"source": "signed_upload"},
        })
        return public_file(row)

    def list_files(self, *, domain: str, user_id: str, client_id: str, category: Optional[str] = None) -> List[Dict]:
        self._check_scope(domain, client_id)
        folder = self._category(domain, category) if category else None
        rows = self.storage.list_files(user_id=user_id, domain=domain, client_no=str(client_id), folder=folder)
        return [public_file(row) for row in rows]

    def signed_url(self, *, domain: str, user_id: str, file_id: str, download: bool = False) -> Dict[str, Any]:
        row = self._owned(domain, user_id, file_id)
        url = self.storage.signed_url(
            row.get("storage_path") or row["url_path"],
            SIGNED_URL_TTL_SECONDS,
            download_name=row.get("name") if download else None,
        )
        return {"url": url, "expires_in": SIGNED_URL_TTL_SECONDS, "file": public_file(row)}

    def delete(self, *, domain: str, user_id: str, file_id: str) -> None:
        self._owned(domain, user_id, file_id)
        if not self.storage.soft_delete(file_id=file_id, user_id=user_id, domain=domain):
            raise FileServiceError("File not found.", 404)

    def retire_client_files(self, *, domain: str, user_id: str, client_id: str) -> int:
        """
        Called when a client/patient is deleted. Record ids are reused (next id = highest + 1), so a
        later record with the same id must never inherit these documents.
        """
        if domain not in CATEGORIES:
            return 0
        return self.storage.soft_delete_client_files(user_id=user_id, domain=domain, client_no=str(client_id))

    def _owned(self, domain: str, user_id: str, file_id: str) -> Dict[str, Any]:
        if domain not in CATEGORIES:
            raise FileServiceError("Unknown workspace.")
        try:
            uuid.UUID(str(file_id))
        except ValueError:
            raise FileServiceError("File not found.", 404)
        row = self.storage.get_file(file_id=str(file_id), user_id=user_id, domain=domain)
        if not row:
            raise FileServiceError("File not found.", 404)
        return row
