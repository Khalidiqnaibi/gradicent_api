from datetime import datetime
from typing import Dict, List, Optional ,Any
from firebase_admin import firestore, storage, get_app
from binder.interfaces.file_storage_adapter import FileStorageAdapter


class FirebaseFileStorageAdapter(FileStorageAdapter):
    '''
    Adapter for the firestore for the files of binder
    '''

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
    
    # Legacy files getter:
    def list_legacy_files(self, *, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch legacy file documents for a user.
        Legacy schema:
        - gid        -> user_id
        - patient_no -> client index (string)
        """

        query = (
            self.db.collection("files")
            .where("gid", "==", user_id)
        )

        results: List[Dict[str, Any]] = []
        for doc in query.stream():
            data = doc.to_dict()
            results.append(data)

        return results
    
    def migrate_legacy_file(self, file) -> Dict:
        
        file_data = {
            "name": file["name"],
            "data": file["data"],
            "file_type": file["file_type"],
            "upload_date": file["upload_date"],
            "deleted": False,
            "deleted_at": None,
            "user_id": file.get("user_id", ""),
            "client_no": file["client_no"],
            "folder": file.get("folder", "misc"),
            "metadata":file.get("metadata", {}),
        }

        self.db.collection("gradicent files").add(file_data)
        return file_data
