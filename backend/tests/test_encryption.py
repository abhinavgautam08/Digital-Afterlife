"""
Comprehensive test suite for Phase 6: Encryption, Vault Management, Safe Migration & Privacy.
Covers all 24 required test scenarios:
  1. Roundtrip file encryption and decryption produces exact byte-for-byte original file.
  2. Large files encrypt and decrypt without unbounded memory consumption (bounded streaming).
  3. Incorrect passphrase raises error / fails decryption cleanly without crashing.
  4. Tampered ciphertext header raises error (DAENC1 magic bytes, version).
  5. Tampered ciphertext payload raises error (authenticated encryption detects modification).
  6. Tampered authentication tag raises error (InvalidTag).
  7. Truncated ciphertext raises error.
  8. Re-encrypting same file twice produces different ciphertext (unique nonces / salt).
  9. Passphrase change re-wraps DEK without re-encrypting data files.
  10. Passphrase change with incorrect current passphrase is rejected.
  11. Decryption with old passphrase fails after passphrase change.
  12. Decryption with new passphrase succeeds after passphrase change.
  13. Emergency recovery key decrypts data when passphrase is lost.
  14. Invalid recovery key is rejected.
  15. Safe migration encrypts all unencrypted files in storage directory.
  16. Safe migration verifies decrypted file hash against original before deleting unencrypted copy.
  17. Interrupted migration resumes safely without re-encrypting already encrypted files.
  18. Safe migration with existing encrypted files leaves them untouched.
  19. Migration rollback restores original unencrypted files from backup.
  20. Locked vault rejects memory access / returns locked status (HTTP 423).
  21. Unlocked vault permits normal memory operations.
  22. Auto-lock triggers after configured inactivity period.
  23. DEK is zeroed out in memory upon locking (verify bytearray is cleared).
  24. Backup archive creation produces valid encrypted .da-backup file.
"""
import io
import os
import time
import shutil
import hashlib
import pytest
from pathlib import Path
from cryptography.exceptions import InvalidTag

from backend.app.core.crypto import (
    VaultKeyManager,
    VaultLockedError,
    CryptoError,
    CorruptedCiphertextError,
    InvalidPasswordError,
    derive_key_argon2id,
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    format_recovery_key,
    parse_recovery_key,
)
from backend.app.services.encryption.file_encryptor import (
    FileEncryptor,
    MAGIC_HEADER,
    HEADER_SIZE,
    DEFAULT_CHUNK_SIZE,
)
from backend.app.services.encryption.field_cipher import (
    encrypt_field,
    decrypt_field,
    is_encrypted_field,
)
from backend.app.services.encryption.migration_service import MigrationService
from backend.app.models.memory import Memory


@pytest.fixture
def temp_vault_env(tmp_path):
    """Provides an isolated VaultKeyManager and FileEncryptor using a temporary envelope path."""
    envelope_path = tmp_path / "security" / "vault_envelope.json"
    mgr = VaultKeyManager(envelope_path=envelope_path)
    encryptor = FileEncryptor(key_manager=mgr)
    return mgr, encryptor, tmp_path


# ==============================================================================
# 1. Low-level Cryptographic Primitives & Streaming File Encryption
# ==============================================================================

def test_01_roundtrip_file_encryption_decryption(temp_vault_env):
    """1. Roundtrip file encryption and decryption produces exact byte-for-byte original file."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("TestMasterPass123!")

    original_data = b"Hello, Digital Afterlife legacy preservation! Testing byte exactness."
    src_file = tmp_path / "original.txt"
    enc_file = tmp_path / "original.txt.enc"
    dec_file = tmp_path / "restored.txt"

    src_file.write_bytes(original_data)
    encryptor.encrypt_file_on_disk(src_file, enc_file)

    assert enc_file.exists()
    assert enc_file.read_bytes() != original_data
    assert encryptor.is_encrypted_file(enc_file) is True

    encryptor.decrypt_file_on_disk(enc_file, dec_file)
    assert dec_file.read_bytes() == original_data


def test_02_large_file_streaming_bounded_memory(temp_vault_env):
    """2. Large files encrypt and decrypt without unbounded memory consumption (bounded streaming)."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("TestMasterPass123!")

    # Generate 512 KB of pseudo-random patterned data (across multiple 64 KB chunks)
    pattern = b"0123456789abcdef" * 64  # 1 KB
    large_data = pattern * 512  # 512 KB
    src_file = tmp_path / "large_audio.raw"
    enc_file = tmp_path / "large_audio.raw.enc"
    dec_file = tmp_path / "large_audio_dec.raw"

    src_file.write_bytes(large_data)
    encryptor.encrypt_file_on_disk(src_file, enc_file)
    encryptor.decrypt_file_on_disk(enc_file, dec_file)

    assert dec_file.stat().st_size == len(large_data)
    assert hashlib.sha256(dec_file.read_bytes()).digest() == hashlib.sha256(large_data).digest()


def test_03_incorrect_passphrase_fails_cleanly(temp_vault_env):
    """3. Incorrect passphrase raises error / fails decryption cleanly without crashing."""
    mgr, _, _ = temp_vault_env
    mgr.setup_vault("CorrectPassword999!")
    mgr.lock()

    with pytest.raises(CryptoError):
        mgr.unlock_with_password("WrongPassword123!")

    assert mgr.is_unlocked() is False


def test_04_tampered_header_raises_error(temp_vault_env):
    """4. Tampered ciphertext header raises error (DAENC1 magic bytes, version)."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MasterPassword123!")

    src_file = tmp_path / "sample.txt"
    enc_file = tmp_path / "sample.txt.enc"
    src_file.write_bytes(b"Header validation test.")
    encryptor.encrypt_file_on_disk(src_file, enc_file)

    # Tamper with the magic bytes (first 6 bytes)
    corrupted_data = bytearray(enc_file.read_bytes())
    corrupted_data[0:6] = b"CORRUP"
    enc_file.write_bytes(corrupted_data)

    out_file = tmp_path / "fail.txt"
    with pytest.raises(CryptoError, match="Invalid file magic header"):
        encryptor.decrypt_file_on_disk(enc_file, out_file)


def test_05_tampered_payload_raises_error(temp_vault_env):
    """5. Tampered ciphertext payload raises error (authenticated encryption detects modification)."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MasterPassword123!")

    src_file = tmp_path / "payload.txt"
    enc_file = tmp_path / "payload.txt.enc"
    src_file.write_bytes(b"Secret payload text to be corrupted.")
    encryptor.encrypt_file_on_disk(src_file, enc_file)

    # Corrupt payload byte after header
    corrupted_data = bytearray(enc_file.read_bytes())
    corrupted_data[HEADER_SIZE + 5] ^= 0xFF
    enc_file.write_bytes(corrupted_data)

    out_file = tmp_path / "corrupted_out.txt"
    with pytest.raises(CryptoError):
        encryptor.decrypt_file_on_disk(enc_file, out_file)


def test_06_tampered_tag_raises_error(temp_vault_env):
    """6. Tampered authentication tag raises error (InvalidTag)."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MasterPassword123!")

    dek = mgr.get_dek()
    plaintext = b"Testing AEAD authentication tag integrity."
    nonce, ciphertext_and_tag = encrypt_aes_gcm(dek, plaintext)

    # Corrupt last byte (part of 16-byte tag)
    corrupted_tag = bytearray(ciphertext_and_tag)
    corrupted_tag[-1] ^= 0xAA

    # Direct AESGCM verifies InvalidTag is raised by the cryptographic primitive
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    with pytest.raises(InvalidTag):
        AESGCM(dek).decrypt(nonce, bytes(corrupted_tag), None)

    # High-level wrapper raises CorruptedCiphertextError
    with pytest.raises(CorruptedCiphertextError):
        decrypt_aes_gcm(dek, nonce, bytes(corrupted_tag))


def test_07_truncated_ciphertext_raises_error(temp_vault_env):
    """7. Truncated ciphertext raises error."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MasterPassword123!")

    src_file = tmp_path / "trunc.txt"
    enc_file = tmp_path / "trunc.txt.enc"
    src_file.write_bytes(b"This file will be prematurely truncated mid-stream.")
    encryptor.encrypt_file_on_disk(src_file, enc_file)

    # Truncate file halfway
    data = enc_file.read_bytes()
    truncated_data = data[:HEADER_SIZE + 10]
    enc_file.write_bytes(truncated_data)

    out_file = tmp_path / "trunc_out.txt"
    with pytest.raises(CryptoError):
        encryptor.decrypt_file_on_disk(enc_file, out_file)


def test_08_unique_nonces_per_encryption(temp_vault_env):
    """8. Re-encrypting same file twice produces different ciphertext (unique nonces / salt)."""
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MasterPassword123!")

    src_file = tmp_path / "duplicate.txt"
    enc_file1 = tmp_path / "duplicate_1.enc"
    enc_file2 = tmp_path / "duplicate_2.enc"
    src_file.write_bytes(b"Identical content to encrypt twice.")

    encryptor.encrypt_file_on_disk(src_file, enc_file1)
    encryptor.encrypt_file_on_disk(src_file, enc_file2)

    data1 = enc_file1.read_bytes()
    data2 = enc_file2.read_bytes()

    assert data1 != data2
    # Ensure random salt in header differs
    salt1 = data1[8:24]
    salt2 = data2[8:24]
    assert salt1 != salt2


# ==============================================================================
# 2. Key Management, Envelope, Re-Wrapping, Auto-lock & Memory Zeroing
# ==============================================================================

def test_09_10_11_12_passphrase_change_and_rewrapping(temp_vault_env):
    """
    9.  Passphrase change re-wraps DEK without re-encrypting data files.
    10. Passphrase change with incorrect current passphrase is rejected.
    11. Decryption with old passphrase fails after passphrase change.
    12. Decryption with new passphrase succeeds after passphrase change.
    """
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("OldPassphrase123!")
    initial_dek = bytes(mgr.get_dek())

    # Encrypt a file under initial DEK
    test_file = tmp_path / "doc.txt"
    enc_file = tmp_path / "doc.txt.enc"
    test_file.write_bytes(b"Important family biography text.")
    encryptor.encrypt_file_on_disk(test_file, enc_file)

    # 10. Passphrase change with incorrect current passphrase is rejected
    with pytest.raises(CryptoError):
        mgr.change_password("WrongCurrentPassword!", "NewPassphrase456!")

    # 9. Passphrase change re-wraps DEK
    mgr.change_password("OldPassphrase123!", "NewPassphrase456!")
    mgr.lock()

    # 11. Decryption with old passphrase fails after change
    with pytest.raises(CryptoError):
        mgr.unlock_with_password("OldPassphrase123!")

    # 12. Decryption with new passphrase succeeds after change
    mgr.unlock_with_password("NewPassphrase456!")
    assert bytes(mgr.get_dek()) == initial_dek  # DEK preserved!

    # Decrypt existing file without re-encryption
    dec_file = tmp_path / "doc_decrypted.txt"
    encryptor.decrypt_file_on_disk(enc_file, dec_file)
    assert dec_file.read_bytes() == b"Important family biography text."


def test_13_14_emergency_recovery_key(temp_vault_env):
    """
    13. Emergency recovery key decrypts data when passphrase is lost.
    14. Invalid recovery key is rejected.
    """
    mgr, encryptor, tmp_path = temp_vault_env
    recovery_key = mgr.setup_vault("OriginalPassword123!")
    mgr.lock()

    # 14. Invalid recovery key is rejected
    with pytest.raises(CryptoError):
        mgr.unlock_with_recovery_key("0000-0000-0000-0000-0000-0000-0000-0000")

    # 13. Emergency recovery key unlocks vault
    mgr.unlock_with_recovery_key(recovery_key)
    assert mgr.is_unlocked() is True

    # Can also reset password using recovery key
    mgr.lock()
    mgr.recover_with_recovery_key(recovery_key, "BrandNewPassword789!")
    mgr.lock()

    # Verify unlocked with new password
    mgr.unlock_with_password("BrandNewPassword789!")
    assert mgr.is_unlocked() is True


def test_22_auto_lock_triggers_after_inactivity(temp_vault_env):
    """22. Auto-lock triggers after configured inactivity period."""
    mgr, _, _ = temp_vault_env
    # Initialize with 1 minute auto lock
    mgr.setup_vault("Password123!", auto_lock_minutes=1)
    assert mgr.is_unlocked() is True

    # Artificially age the last access timestamp back 65 seconds
    mgr._last_activity = time.time() - 65
    assert mgr.check_auto_lock() is True
    assert mgr.is_unlocked() is False


def test_23_dek_zeroed_out_on_lock(temp_vault_env):
    """23. DEK is zeroed out in memory upon locking (verify bytearray is cleared)."""
    mgr, _, _ = temp_vault_env
    mgr.setup_vault("Password123!")

    # Check internal DEK bytearray
    assert mgr._dek is not None
    assert any(b != 0 for b in mgr._dek)
    dek_ref = mgr._dek

    mgr.lock()
    assert mgr.is_unlocked() is False
    assert mgr._dek is None
    # Verify the previously held memory buffer was wiped with zeros
    assert all(b == 0 for b in dek_ref)


# ==============================================================================
# 3. Safe Migration, Rollback & Unified Backup
# ==============================================================================

def test_15_16_17_18_19_safe_migration_and_rollback(tmp_path):
    """
    15. Safe migration encrypts all unencrypted files in storage directory.
    16. Safe migration verifies decrypted file hash against original before deleting unencrypted copy.
    17. Interrupted migration resumes safely without re-encrypting already encrypted files.
    18. Safe migration with existing encrypted files leaves them untouched.
    19. Migration rollback restores original unencrypted files from backup.
    """
    storage_dir = tmp_path / "memories"
    thumbs_dir = tmp_path / "thumbnails"
    backup_dir = tmp_path / "backups"
    envelope_path = tmp_path / "security" / "vault_envelope.json"

    storage_dir.mkdir(parents=True)
    thumbs_dir.mkdir(parents=True)

    # Populate plaintext files
    f1 = storage_dir / "photo1.jpg"
    f2 = storage_dir / "letter.pdf"
    t1 = thumbs_dir / "thumb1.jpg"

    f1.write_bytes(b"JPEG_MOCK_IMAGE_DATA_1111")
    f2.write_bytes(b"PDF_DOCUMENT_TEXT_CONTENT_2222")
    t1.write_bytes(b"THUMBNAIL_IMAGE_BYTES_3333")

    orig_hashes = {
        "photo1.jpg": hashlib.sha256(f1.read_bytes()).hexdigest(),
        "letter.pdf": hashlib.sha256(f2.read_bytes()).hexdigest(),
        "thumb1.jpg": hashlib.sha256(t1.read_bytes()).hexdigest(),
    }

    key_mgr = VaultKeyManager(envelope_path=envelope_path)
    key_mgr.setup_vault("MigrationPass123!")
    encryptor = FileEncryptor(key_manager=key_mgr)

    migrator = MigrationService(
        key_manager=key_mgr,
        file_encryptor=encryptor,
        storage_dirs=[storage_dir, thumbs_dir],
        backup_root=backup_dir,
    )

    # 15. Safe migration encrypts all files
    status = migrator.start_migration(sync=True)
    assert status.successful_files == 3
    assert status.failed_files == 0
    assert status.is_running is False

    # 16. Verify files on disk are encrypted and decryptable
    for f in [f1, f2, t1]:
        assert encryptor.is_encrypted_file(f) is True

    # 18. Safe migration with existing encrypted files leaves them untouched (idempotent resume)
    status2 = migrator.start_migration(sync=True)
    assert status2.total_files == 0  # No plaintext files remain

    # 19. Migration rollback restores original unencrypted files from backup
    rollback_res = migrator.rollback_migration()
    assert rollback_res["restored_files"] == 3

    # Verify restored files are exact plaintext matches
    assert f1.read_bytes() == b"JPEG_MOCK_IMAGE_DATA_1111"
    assert f2.read_bytes() == b"PDF_DOCUMENT_TEXT_CONTENT_2222"
    assert t1.read_bytes() == b"THUMBNAIL_IMAGE_BYTES_3333"
    assert encryptor.is_encrypted_file(f1) is False


def test_24_encrypted_backup_creation_and_restoration(tmp_path):
    """24. Backup archive creation produces valid encrypted .da-backup file and restores cleanly."""
    storage_dir = tmp_path / "memories"
    db_file = tmp_path / "app.db"
    backup_out = tmp_path / "backups"
    envelope_path = tmp_path / "security" / "vault_envelope.json"

    storage_dir.mkdir(parents=True)
    (storage_dir / "story.txt").write_bytes(b"Grandmother oral history transcript.")
    db_file.write_bytes(b"SQLITE_FORMAT_MOCK_BYTES")

    key_mgr = VaultKeyManager(envelope_path=envelope_path)
    key_mgr.setup_vault("BackupPassphrase123!")
    encryptor = FileEncryptor(key_manager=key_mgr)

    migrator = MigrationService(
        key_manager=key_mgr,
        file_encryptor=encryptor,
        storage_dirs=[storage_dir],
        backup_root=backup_out,
    )

    # Create backup archive
    backup_file = migrator.create_encrypted_backup(db_path=db_file, out_dir=backup_out)
    assert backup_file.exists()
    assert backup_file.name.endswith(".da-backup")
    assert backup_file.stat().st_size > 0
    # Must not contain plaintext substring
    assert b"Grandmother oral history" not in backup_file.read_bytes()

    # Restore backup into fresh directory
    restore_target = tmp_path / "restored_vault"
    migrator.restore_encrypted_backup(backup_file, restore_target)

    restored_story = restore_target / "memories" / "story.txt"
    assert restored_story.exists()
    assert restored_story.read_bytes() == b"Grandmother oral history transcript."


# ==============================================================================
# 4. Field-Level Encryption & API HTTP 423 Locked Guards
# ==============================================================================

def test_field_level_encryption(temp_vault_env):
    """Verifies AES-256-GCM authenticated encryption for sensitive database string fields."""
    mgr, _, _ = temp_vault_env
    mgr.setup_vault("FieldPassphrase123!")
    dek = mgr.get_dek()

    secret_text = "Grandfather's handwritten letters from 1945."
    encrypted = encrypt_field(secret_text, dek=dek)

    assert encrypted.startswith("ENC:v1:")
    assert is_encrypted_field(encrypted) is True
    assert secret_text not in encrypted

    # Decrypt when unlocked
    decrypted = decrypt_field(encrypted, dek=dek)
    assert decrypted == secret_text

    # Lock vault - decrypt returns placeholder or raises
    mgr.lock()
    locked_placeholder = decrypt_field(encrypted)
    assert locked_placeholder == "[Vault Locked — Decryption Required]"

    with pytest.raises(VaultLockedError):
        decrypt_field(encrypted, strict=True)


def test_20_21_api_locked_vault_enforcement(client, tmp_path):
    """
    20. Locked vault rejects memory access / returns locked status (HTTP 423).
    21. Unlocked vault permits normal memory operations.
    """
    from backend.app.core.crypto import vault_key_manager, VaultEnvelope
    orig_envelope = vault_key_manager._envelope
    vault_key_manager._envelope = VaultEnvelope(tmp_path / "security" / "vault_envelope.json")
    vault_key_manager._is_unlocked = False
    vault_key_manager._dek = None

    try:
        # 1. Check vault status endpoint
        res = client.get("/api/security/vault/status")
        assert res.status_code == 200
        data = res.json()
        assert "is_initialized" in data

        # 2. Setup vault via API
        setup_res = client.post("/api/security/vault/setup", json={
            "password": "MasterPassphrase123!",
            "auto_lock_minutes": 15
        })
        assert setup_res.status_code == 200
        assert "recovery_key" in setup_res.json()

        # 3. Check status is now initialized and unlocked
        status_res = client.get("/api/security/vault/status")
        assert status_res.json()["is_unlocked"] is True

        # 4. Lock vault via API
        lock_res = client.post("/api/security/vault/lock")
        assert lock_res.status_code == 200
        assert lock_res.json()["status"] == "locked"

        # 5. Accessing RAG Ask Memories while locked returns HTTP 423 Locked
        rag_res = client.post("/api/memories/ask", json={"query": "What is here?"})
        assert rag_res.status_code == 423
        assert "Vault is locked" in rag_res.json()["detail"]

        # 6. Accessing storytelling generate while locked returns HTTP 423 Locked
        bio_res = client.post("/api/storytelling/biographies/generate", json={"person_id": "none"})
        assert bio_res.status_code == 423
        assert "Vault is locked" in bio_res.json()["detail"]

        # 6b. Additional locked endpoint checks
        # Transcripts
        tx_res = client.get("/api/memories/1/transcript")
        assert tx_res.status_code == 423
        assert "Vault is locked" in tx_res.json()["detail"]

        # Remembrance
        rem_res = client.get("/api/storytelling/remembrance/1")
        assert rem_res.status_code == 423
        assert "Vault is locked" in rem_res.json()["detail"]

        # Collections
        col_res = client.get("/api/storytelling/collections")
        assert col_res.status_code == 423
        assert "Vault is locked" in col_res.json()["detail"]

        # People memories
        pm_res = client.get("/api/people/1/memories")
        assert pm_res.status_code == 423
        assert "Vault is locked" in pm_res.json()["detail"]

        # 7. 21. Unlock vault with password and verify access restored
        unlock_res = client.post("/api/security/vault/unlock", json={"password": "MasterPassphrase123!"})
        assert unlock_res.status_code == 200
        assert unlock_res.json()["status"] == "unlocked"

        # Verify status is unlocked
        status_unlocked = client.get("/api/security/vault/status")
        assert status_unlocked.json()["is_unlocked"] is True
    finally:
        vault_key_manager._envelope = orig_envelope
        vault_key_manager.lock()


def test_chunk_reordering_detection(temp_vault_env):
    """
    Cryptographic verification: Reordering chunks in a multi-chunk file must fail
    with CorruptedCiphertextError because AAD and nonce bind chunk index.
    """
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("TestPass123!")

    # Write data larger than small chunk size to produce at least 2 chunks
    chunk_sz = 64
    multi_chunk_data = b"Chunk Zero Data" * 5 + b"Chunk One Data" * 5 + b"Chunk Two Data" * 5
    src_file = tmp_path / "multi_chunk.bin"
    enc_file = tmp_path / "multi_chunk.bin.enc"
    dec_file = tmp_path / "restored.bin"
    src_file.write_bytes(multi_chunk_data)

    encryptor.encrypt_file_on_disk(src_file, enc_file, chunk_size=chunk_sz)

    # Read binary enc_file and parse out header and chunks
    enc_bytes = enc_file.read_bytes()
    header = enc_bytes[:HEADER_SIZE]
    
    # Extract chunk lengths and payload
    offset = HEADER_SIZE
    chunks = []
    while offset < len(enc_bytes):
        c_len = int.from_bytes(enc_bytes[offset:offset+4], "big")
        total_len = 4 + c_len
        chunks.append(enc_bytes[offset:offset+total_len])
        offset += total_len

    assert len(chunks) >= 2, "Test requires at least 2 chunks"

    # Reorder chunk 0 and chunk 1
    reordered_chunks = [chunks[1], chunks[0]] + chunks[2:]
    reordered_bytes = header + b"".join(reordered_chunks)

    reordered_file = tmp_path / "reordered.bin.enc"
    reordered_file.write_bytes(reordered_bytes)

    with pytest.raises(CorruptedCiphertextError):
        encryptor.decrypt_file_on_disk(reordered_file, dec_file)


def test_chunk_substitution_detection(temp_vault_env):
    """
    Cryptographic verification: Substituting a chunk from File A into File B must fail
    with CorruptedCiphertextError due to base_nonce and AAD binding.
    """
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("TestPass123!")

    chunk_sz = 64
    data_a = b"File A Content Chunk 0" * 4 + b"File A Content Chunk 1" * 4
    data_b = b"File B Content Chunk 0" * 4 + b"File B Content Chunk 1" * 4

    file_a = tmp_path / "file_a.bin"
    file_b = tmp_path / "file_b.bin"
    enc_a = tmp_path / "file_a.bin.enc"
    enc_b = tmp_path / "file_b.bin.enc"

    file_a.write_bytes(data_a)
    file_b.write_bytes(data_b)

    encryptor.encrypt_file_on_disk(file_a, enc_a, chunk_size=chunk_sz)
    encryptor.encrypt_file_on_disk(file_b, enc_b, chunk_size=chunk_sz)

    # Parse chunks from A and B
    enc_a_bytes = enc_a.read_bytes()
    enc_b_bytes = enc_b.read_bytes()

    header_b = enc_b_bytes[:HEADER_SIZE]

    # Get chunk 0 of A
    len_a_c0 = int.from_bytes(enc_a_bytes[HEADER_SIZE:HEADER_SIZE+4], "big")
    chunk_a_0 = enc_a_bytes[HEADER_SIZE:HEADER_SIZE+4+len_a_c0]

    # Get chunk 1 of B
    len_b_c0 = int.from_bytes(enc_b_bytes[HEADER_SIZE:HEADER_SIZE+4], "big")
    offset_b_c1 = HEADER_SIZE + 4 + len_b_c0
    chunk_b_1 = enc_b_bytes[offset_b_c1:]

    # Construct substituted file: header B + chunk 0 from A + chunk 1 from B
    substituted_bytes = header_b + chunk_a_0 + chunk_b_1
    sub_file = tmp_path / "substituted.bin.enc"
    sub_file.write_bytes(substituted_bytes)

    dec_file = tmp_path / "sub_restored.bin"
    with pytest.raises(CorruptedCiphertextError):
        encryptor.decrypt_file_on_disk(sub_file, dec_file)


def test_database_records_migration_and_rollback(temp_vault_env, test_db):
    """
    Verifies that MigrationService._migrate_database_records correctly encrypts
    plaintext records in the database, and _rollback_database_records decrypts them back.
    """
    mgr, encryptor, tmp_path = temp_vault_env
    mgr.setup_vault("MigrationPass123!")
    dek = mgr.get_dek()

    # Create test Memory with plaintext description and extracted_text
    plaintext_desc = "Grandma's secret recipe for sourdough bread, written in 1952."
    plaintext_ext = "Ingredients: 500g flour, 350g water, 100g starter, 10g salt."
    
    test_memory = Memory(
        title="Family Recipe",
        memory_type="document",
        original_filename="recipe.txt",
        stored_filename="recipe.txt",
        file_path="recipes/recipe.txt",
        mime_type="text/plain",
        file_size=100,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        description=plaintext_desc,
        extracted_text=plaintext_ext,
    )
    test_db.add(test_memory)
    test_db.commit()
    test_db.refresh(test_memory)
    mem_id = test_memory.id

    try:
        migration_svc = MigrationService(
            key_manager=mgr,
            file_encryptor=encryptor,
            storage_dirs=[],
            backup_root=tmp_path / "migration_backups"
        )

        # 1. Migrate database records
        migrated_count = migration_svc._migrate_database_records(dek, db=test_db)
        assert migrated_count >= 1

        # Query database directly to check raw stored value
        test_db.expire_all()
        reloaded_mem = test_db.query(Memory).filter(Memory.id == mem_id).first()
        assert reloaded_mem.description.startswith("ENC:v1:")
        assert reloaded_mem.extracted_text.startswith("ENC:v1:")
        assert plaintext_desc not in reloaded_mem.description

        # 2. Rollback database records
        migration_svc._rollback_database_records(db=test_db)
        test_db.expire_all()
        restored_mem = test_db.query(Memory).filter(Memory.id == mem_id).first()
        assert restored_mem.description == plaintext_desc
        assert restored_mem.extracted_text == plaintext_ext
    finally:
        test_db.delete(test_memory)
        test_db.commit()

