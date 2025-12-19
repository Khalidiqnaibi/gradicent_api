from datetime import datetime
from typing import Dict, List, Optional
from firebase_admin import firestore, storage, get_app
from binder.interfaces.file_storage_adapter import FileStorageAdapter


class FirebaseFileStorageAdapter(FileStorageAdapter):
    def __init__(self):
        self._db = None
        self._bucket = None

    @property
    def db(self):
        if self._db is None:
            self._db = firestore.client()
        return self._db

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = storage.bucket()
        return self._bucket

    def upload_file(self, *, file, filename: str, content_type: str, metadata: Dict) -> Dict:
        client_no = metadata.get("client_no", "unknown")
        folder = metadata.get("folder", "misc")

        blob_path = f"{client_no}/{folder}/{datetime.now().timestamp()}_{filename}"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_file(file.stream, content_type=content_type)
        blob.make_public()

        file_data = {
            "name": filename,
            "data": blob.public_url,
            "file_type": content_type,
            "upload_date": datetime.now().isoformat(),
            "deleted": False,
            "deleted_at": None,
            **metadata,
        }

        self.db.collection("gradicent files").add(file_data)
        return file_data

    def list_files(self, *, client_no: str, user_id: str, folder: Optional[str] = None) -> List[Dict]:
        query = (
            self.db.collection("gradicent files")
            .where("client_no", "==", client_no)
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
        )

        results = []
        for doc in query.stream():
            data = doc.to_dict()
            if folder and data.get("folder") != folder:
                continue
            results.append(data)

        return results

    def soft_delete(self, *, file_url: str) -> bool:
        query = (
            self.db.collection("gradicent files")
            .where("data", "==", file_url)
            .limit(1)
            .stream()
        )

        for doc in query:
            doc.reference.update({
                "deleted": True,
                "deleted_at": datetime.now().isoformat(),
            })
            return True

        return False
