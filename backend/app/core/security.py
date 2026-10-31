"""
Security and validation module for Digital Afterlife.
Provides:
- Path traversal prevention
- Filename sanitization
- MIME and extension validation
- Encryption abstraction (prepared for Phase 2 AES-256-GCM)
"""
import abc
import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from backend.app.core.config import settings
from backend.app.core.logging import logger


class SecurityValidationError(Exception):
    """Raised when security or file validation checks fail."""
    pass


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an incoming filename to prevent path traversal and shell injection.
    Strips directory separators, null bytes, and non-whitelisted characters.
    """
    if not filename:
        raise SecurityValidationError("Filename cannot be empty.")

    # Remove null bytes
    if "\x00" in filename:
        raise SecurityValidationError("Filename contains null byte.")

    # Extract purely the basename to prevent path traversal
    clean_name = os.path.basename(filename)
    clean_name = clean_name.replace("/", "").replace("\\", "").strip()

    # Reject any directory traversal indicators
    if clean_name in (".", "..") or ".." in clean_name:
        raise SecurityValidationError("Path traversal pattern detected in filename.")

    # Replace spaces and unusual characters, keep alphanumeric, dots, hyphens, and underscores
    clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)

    if not clean_name or clean_name.startswith("."):
        clean_name = f"memory_{uuid.uuid4().hex[:8]}"

    return clean_name


def generate_safe_filename(original_filename: str) -> Tuple[str, str]:
    """
    Generates a secure internal stored filename using UUID4 while preserving the sanitized extension.
    Returns (stored_filename, extension).
    """
    clean_original = sanitize_filename(original_filename)
    ext = Path(clean_original).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise SecurityValidationError(
            f"File extension '{ext}' is not permitted. Allowed: {sorted(list(settings.ALLOWED_EXTENSIONS))}"
        )

    stored_name = f"{uuid.uuid4().hex}{ext}"
    return stored_name, ext


def validate_file_metadata(original_filename: str, content_type: str, file_size: int) -> None:
    """
    Validates extension, MIME type, and size constraints.
    """
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise SecurityValidationError(f"File size exceeds maximum allowed limit of {max_mb} MB.")

    if file_size <= 0:
        raise SecurityValidationError("Uploaded file is empty.")

    ext = Path(sanitize_filename(original_filename)).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise SecurityValidationError(f"Disallowed file extension: {ext}")

    # Normalize mime type
    mime = content_type.lower().split(";")[0].strip()
    if mime not in settings.ALLOWED_MIME_TYPES:
        raise SecurityValidationError(f"Disallowed MIME type: {mime}")


def compute_sha256(data: bytes) -> str:
    """Computes SHA-256 digest of binary content for integrity and duplicate prevention."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Encryption Abstraction (Phase 6 AES-256-GCM Vault Integration)
# ---------------------------------------------------------------------------

class BaseEncryptionProvider(abc.ABC):
    """Abstract Base Class for at-rest memory encryption providers."""

    @property
    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Indicates whether active encryption is enabled."""
        pass

    @abc.abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypts data."""
        pass

    @abc.abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypts data."""
        pass


class NoOpEncryptionProvider(BaseEncryptionProvider):
    """
    Maintains storage transparency when encryption is not initialized.
    """

    @property
    def is_enabled(self) -> bool:
        return False

    def encrypt(self, plaintext: bytes) -> bytes:
        return plaintext

    def decrypt(self, ciphertext: bytes) -> bytes:
        return ciphertext


class AES256GCMEncryptionProvider(BaseEncryptionProvider):
    """
    Phase 6 Production Authenticated Encryption Provider:
    Uses AES-256-GCM with memory-bounded chunking and unique nonces via VaultKeyManager.
    """

    @property
    def is_enabled(self) -> bool:
        from backend.app.core.crypto import vault_key_manager
        return vault_key_manager.is_initialized()

    def encrypt(self, plaintext: bytes) -> bytes:
        from backend.app.core.crypto import vault_key_manager
        from backend.app.services.encryption.file_encryptor import file_encryptor

        if not vault_key_manager.is_initialized():
            return plaintext  # Uninitialized vault stores plaintext until user sets up encryption

        dek = vault_key_manager.get_dek()
        return file_encryptor.encrypt_bytes(plaintext, dek)

    def decrypt(self, ciphertext: bytes) -> bytes:
        from backend.app.core.crypto import vault_key_manager
        from backend.app.services.encryption.file_encryptor import file_encryptor

        if not file_encryptor.is_encrypted_bytes(ciphertext):
            return ciphertext  # Transparently return legacy plaintext files

        dek = vault_key_manager.get_dek()
        return file_encryptor.decrypt_bytes(ciphertext, dek)


def get_encryption_provider() -> BaseEncryptionProvider:
    """Factory function returning the active vault encryption provider."""
    return AES256GCMEncryptionProvider()

