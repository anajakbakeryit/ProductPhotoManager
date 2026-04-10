"""
Storage service — local filesystem (dev) or GCS (production).
"""
import os
import shutil
import logging
from pathlib import Path

from backend.api.config import settings

logger = logging.getLogger(__name__)


class LocalStorage:
    """Store files on local filesystem (for development)."""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.storage_local_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(self, data: bytes, key: str) -> str:
        """Save bytes to local path. Returns the key."""
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def upload_file(self, source_path: str, key: str) -> str:
        """Copy file to storage. Returns the key."""
        dest = self.base_path / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        return key

    def download(self, key: str) -> bytes:
        """Read file bytes from storage."""
        path = self.base_path / key
        return path.read_bytes()

    def get_path(self, key: str) -> str:
        """Get absolute filesystem path (local only)."""
        return str(self.base_path / key)

    def get_url(self, key: str) -> str:
        """Get URL for serving. For local, use API endpoint."""
        return f"/api/storage/{key}"

    def delete(self, key: str) -> None:
        """Delete file from storage."""
        path = self.base_path / key
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()

    def list_keys(self, prefix: str) -> list[str]:
        """List all keys under prefix."""
        base = self.base_path / prefix
        if not base.exists():
            return []
        return [
            str((base / f).relative_to(self.base_path))
            for f in base.rglob("*") if f.is_file()
        ]


def get_storage() -> LocalStorage:
    """Factory: returns storage backend based on config."""
    # TODO: Add GCS backend when deploying to Cloud Run
    return LocalStorage()
