"""
Tests for security: path traversal protection, MIME/extension whitelisting,
file size constraints, and encryption abstraction.
"""
import io
import pytest
from backend.app.core.security import (
    sanitize_filename,
    generate_safe_filename,
    validate_file_metadata,
    SecurityValidationError,
    get_encryption_provider,
    NoOpEncryptionProvider,
    AES256GCMEncryptionProvider
)
from backend.app.services.storage_service import storage_service


def test_sanitize_filename_prevents_traversal():
    # Direct traversal sequences
    assert sanitize_filename("../../../etc/passwd").startswith("passwd")
    assert sanitize_filename("..\\..\\Windows\\System32\\calc.exe").startswith("calc.exe")
    assert ".." not in sanitize_filename("safe_name.jpg")

    with pytest.raises(SecurityValidationError):
        sanitize_filename("")

    with pytest.raises(SecurityValidationError):
        sanitize_filename("..\x00test.jpg")


def test_storage_service_rejects_path_traversal():
    with pytest.raises(SecurityValidationError):
        storage_service.get_secure_path("../../../outside.txt")


def test_reject_unsupported_extensions(client):
    file_bytes = b"MALICIOUS_EXEC"
    res = client.post(
        "/api/memories",
        data={"title": "Malware attempt", "memory_type": "document"},
        files={"file": ("virus.exe", io.BytesIO(file_bytes), "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "disallowed" in res.json()["detail"].lower() or "not permitted" in res.json()["detail"].lower()


def test_reject_unsupported_mime(client):
    file_bytes = b"SCRIPT_PAYLOAD"
    res = client.post(
        "/api/memories",
        data={"title": "Script attempt", "memory_type": "document"},
        files={"file": ("notes.txt", io.BytesIO(file_bytes), "application/x-sh")}
    )
    assert res.status_code == 400
    assert "mime" in res.json()["detail"].lower()


def test_encryption_abstraction_phase1():
    provider = get_encryption_provider()
    assert isinstance(provider, (NoOpEncryptionProvider, AES256GCMEncryptionProvider))

    test_bytes = b"CONFIDENTIAL_FAMILY_LETTER"
    encrypted = provider.encrypt(test_bytes)
    decrypted = provider.decrypt(encrypted)
    assert decrypted == test_bytes

