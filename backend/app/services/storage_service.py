"""
Storage service for managing files locally on disk.
Guarantees path safety, categorized folder structure (images, audio, video, documents, stories),
prevents traversal outside the storage root, and tracks storage usage accurately.
"""
from pathlib import Path
from typing import Tuple, Optional
import os

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import (
    generate_safe_filename,
    compute_sha256,
    SecurityValidationError,
    get_encryption_provider,
)
from backend.app.services.ingestion.thumbnail_service import thumbnail_service


class StorageService:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = (storage_dir or settings.STORAGE_DIR).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encryption = get_encryption_provider()

        # Ensure category subdirectories
        for cat in ("images", "audio", "video", "documents", "stories"):
            (self.storage_dir / cat).mkdir(parents=True, exist_ok=True)

    def _get_category_folder(self, memory_type: Optional[str]) -> Path:
        """Determines target category folder based on memory type."""
        cat_map = {
            "photograph": self.storage_dir / "images",
            "audio": self.storage_dir / "audio",
            "video": self.storage_dir / "video",
            "document": self.storage_dir / "documents",
            "story": self.storage_dir / "stories",
        }
        return cat_map.get((memory_type or "").lower(), self.storage_dir / "documents")

    def get_secure_path(self, stored_filename: str, memory_type: Optional[str] = None) -> Path:
        """
        Resolves stored filename inside storage directory and verifies it does not traverse.
        Searches category subdirectories and root storage for backwards compatibility.
        """
        if not stored_filename or ".." in stored_filename:
            raise SecurityValidationError("Path traversal attack detected in filename.")

        # Strip directory separators from filename to prevent traversal
        clean_name = os.path.basename(stored_filename)

        # 1. Check if category folder contains the file
        if memory_type:
            cat_dir = self._get_category_folder(memory_type)
            cat_path = (cat_dir / clean_name).resolve()
            if cat_path.exists():
                cat_path.relative_to(self.storage_dir)
                return cat_path

        # 2. Search category subfolders
        for sub in ("images", "audio", "video", "documents", "stories"):
            candidate = (self.storage_dir / sub / clean_name).resolve()
            if candidate.exists():
                candidate.relative_to(self.storage_dir)
                return candidate

        # 3. Check directly in storage root (legacy Phase 1 files)
        resolved_path = (self.storage_dir / clean_name).resolve()
        try:
            resolved_path.relative_to(self.storage_dir)
        except ValueError:
            raise SecurityValidationError("Path traversal attack detected.")

        return resolved_path

    def save_file(
        self,
        content: bytes,
        original_filename: str,
        memory_type: str = "photograph"
    ) -> Tuple[str, str, int, str]:
        """
        Saves incoming file bytes locally inside the appropriate category folder using a UUID.
        Returns (stored_filename, file_path_str, file_size, sha256_hash).
        """
        stored_filename, _ = generate_safe_filename(original_filename)
        target_dir = self._get_category_folder(memory_type)
        destination_path = (target_dir / stored_filename).resolve()

        # Strict containment verification
        destination_path.relative_to(self.storage_dir)

        content_hash = compute_sha256(content)
        file_size = len(content)

        # Process through encryption abstraction
        processed_content = self.encryption.encrypt(content)

        # Write safely to disk
        destination_path.write_bytes(processed_content)
        logger.info(f"Stored {memory_type} artifact: {stored_filename} in {target_dir.name} ({file_size} bytes)")

        return stored_filename, str(destination_path), file_size, content_hash

    def read_file(self, stored_filename: str, memory_type: Optional[str] = None) -> Tuple[bytes, Path]:
        """Reads file bytes from storage."""
        file_path = self.get_secure_path(stored_filename, memory_type=memory_type)
        if not file_path.exists():
            raise FileNotFoundError(f"Stored file {stored_filename} does not exist.")

        raw_bytes = file_path.read_bytes()
        decrypted_bytes = self.encryption.decrypt(raw_bytes)
        return decrypted_bytes, file_path

    def stream_file(self, stored_filename: str, memory_type: Optional[str] = None):
        """
        Yields decrypted plaintext chunks (64 KB) for streaming playback or preview.
        Memory bounded to ~64 KB.
        Raises VaultLockedError if vault is locked and file is encrypted.
        """
        file_path = self.get_secure_path(stored_filename, memory_type=memory_type)
        if not file_path.exists():
            raise FileNotFoundError(f"Stored file {stored_filename} does not exist.")

        from backend.app.services.encryption.file_encryptor import file_encryptor
        from backend.app.core.crypto import vault_key_manager, VaultLockedError

        if file_encryptor.is_encrypted_file(file_path):
            if not vault_key_manager.is_unlocked():
                raise VaultLockedError("Vault is locked. Cannot stream encrypted memory.")
            dek = vault_key_manager.get_dek()
            with open(file_path, "rb") as fin:
                yield from file_encryptor.decrypt_stream(fin, dek)
        else:
            with open(file_path, "rb") as fin:
                while chunk := fin.read(64 * 1024):
                    yield chunk

    def delete_file(self, stored_filename: str, thumbnail_path: Optional[str] = None) -> bool:
        """Deletes a file and its associated thumbnail from local storage."""
        deleted = False
        try:
            file_path = self.get_secure_path(stored_filename)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted stored file: {stored_filename}")
                deleted = True
        except Exception as e:
            logger.error(f"Failed to delete file {stored_filename}: {e}")

        # Delete thumbnail if present
        if thumbnail_path:
            try:
                t_path = thumbnail_service.get_thumbnail_path(thumbnail_path)
                if t_path and t_path.exists():
                    t_path.unlink()
                    logger.debug(f"Deleted thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to delete thumbnail {thumbnail_path}: {e}")

        return deleted

    def get_storage_stats(self) -> dict:
        """Calculates total disk usage of memories and thumbnails recursively."""
        total_size = 0
        file_count = 0

        # Recursively scan memories directory
        for entry in self.storage_dir.rglob("*"):
            if entry.is_file() and entry.name != ".gitkeep":
                file_count += 1
                try:
                    total_size += entry.stat().st_size
                except OSError:
                    pass

        # Include thumbnails directory
        if settings.THUMBNAILS_DIR.exists():
            for entry in settings.THUMBNAILS_DIR.glob("*"):
                if entry.is_file() and entry.name != ".gitkeep":
                    file_count += 1
                    try:
                        total_size += entry.stat().st_size
                    except OSError:
                        pass

        # Human readable formatted size
        if total_size < 1024:
            formatted = f"{total_size} B"
        elif total_size < 1024 * 1024:
            formatted = f"{total_size / 1024:.1f} KB"
        elif total_size < 1024 * 1024 * 1024:
            formatted = f"{total_size / (1024 * 1024):.1f} MB"
        else:
            formatted = f"{total_size / (1024 * 1024 * 1024):.2f} GB"

        return {
            "storage_directory": str(self.storage_dir),
            "total_files": file_count,
            "total_bytes": total_size,
            "formatted_size": formatted
        }


storage_service = StorageService()
