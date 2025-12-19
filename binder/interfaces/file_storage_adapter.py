"""
file_storage_adapter.py
-----------------------
Abstract adapter for file storage and metadata persistence.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class FileStorageAdapter(ABC):
    """Abstract interface for file storage backends."""

    # Upload
    @abstractmethod
    def upload_file(
        self,
        *,
        file,
        filename: str,
        content_type: str,
        metadata: Dict,
    ) -> Dict:
        """
        Store a file and its metadata.

        Returns:
            dict: stored file metadata (including public URL or identifier)
        """
        raise NotImplementedError

    # Retrieval
    @abstractmethod
    def list_files(
        self,
        *,
        patient_no: str,
        google_id: str,
        folder: Optional[str] = None,
    ) -> List[Dict]:
        """List files for a patient."""
        raise NotImplementedError

    # Soft delete
    @abstractmethod
    def soft_delete(self, *, file_url: str) -> bool:
        """Soft-delete a file."""
        raise NotImplementedError
