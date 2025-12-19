"""
file_service.py
---------------
Domain-level file operations.
"""

from typing import Dict, List, Optional
from binder.interfaces.file_storage_adapter import FileStorageAdapter


class FileService:
    '''
    service for file operations
    that uses a FileStorageAdapter
    and provides domain logic
    
    inputs:
    - storage_adapter: FileStorageAdapter implementation
    
    outputs:
    ```python
    - upload(file, client_no, folder, user_id) -> Dict
    - list_files(client_no, user_id, folder) -> List[Dict]   
    - delete(file_url) -> bool
    
    docstring examples:
    file_service = FileService(FirebaseFileStorageAdapter())
    uploaded_file = file_service.upload(
        file=my_file,
        client_no="12345",
        folder="lab_reports",
        user_id="google-uid-67890",
    )
    
    files = file_service.list_files(
        client_no="12345",
        user_id="google-uid-67890",
        folder="lab_reports",
    )
    
    deleted = file_service.delete(file_url="https://storage.googleapis.com/...")
    ```
    '''
    def __init__(self, storage_adapter: FileStorageAdapter):
        self.storage = storage_adapter

    def upload(
        self,
        *,
        file,
        client_no: str,
        folder: str,
        user_id: str,
    ) -> Dict:
        return self.storage.upload_file(
            file=file,
            filename=file.filename,
            content_type=file.content_type,
            metadata={
                "client_no": client_no,
                "folder": folder,
                "user_id": user_id,
            },
        )

    def list_files(
        self,
        *,
        client_no: str,
        user_id: str,
        folder: Optional[str] = None,
    ) -> List[Dict]:
        return self.storage.list_files(
            client_no=client_no,
            user_id=user_id,
            folder=folder,
        )

    def delete(self, *, file_url: str) -> bool:
        return self.storage.soft_delete(file_url=file_url)
