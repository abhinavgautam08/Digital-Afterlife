"""
Core Cryptographic Engine for Digital Afterlife.
Phase 6: Authenticated AES-256-GCM encryption, Argon2id key derivation,
secure key wrapping, recovery key architecture, and memory lifecycle management.
"""
import json
import os
import re
import secrets
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import argon2
from argon2.low_level import hash_secret_raw, Type

from backend.app.core.config import settings
from backend.app.core.logging import logger


class CryptoError(Exception):
    """Base error for cryptographic operations."""
    pass


class VaultLockedError(CryptoError):
    """Raised when an operation requires an unlocked vault but the vault is locked."""
    pass


class InvalidPasswordError(CryptoError):
    """Raised when password verification or key unwrapping fails."""
    pass


class CorruptedCiphertextError(CryptoError):
    """Raised when ciphertext is truncated, altered, or fails authentication tag verification."""
    pass


# -----------------------------------------------------------------------------
# Key Derivation (Argon2id)
# -----------------------------------------------------------------------------

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MB RAM
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 32        # 256 bits for AES-256


def derive_key_argon2id(
    passphrase: str,
    salt: bytes,
    time_cost: int = ARGON2_TIME_COST,
    memory_cost: int = ARGON2_MEMORY_COST,
    parallelism: int = ARGON2_PARALLELISM
) -> bytes:
    """
    Derives a 256-bit Key Encryption Key (KEK) using Argon2id.
    Argon2id provides state-of-the-art resistance to both GPU and side-channel attacks.
    """
    if not passphrase:
        raise InvalidPasswordError("Passphrase cannot be empty.")
    if len(salt) < 16:
        raise CryptoError("Salt must be at least 16 bytes.")

    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID
    )


# -----------------------------------------------------------------------------
# AES-256-GCM Primitives
# -----------------------------------------------------------------------------

def encrypt_aes_gcm(key: bytes, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Encrypts plaintext with AES-256-GCM.
    Returns (12-byte random nonce, ciphertext_with_tag).
    """
    if len(key) != 32:
        raise CryptoError("AES-256 key must be exactly 32 bytes.")
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce, ciphertext_and_tag


def decrypt_aes_gcm(key: bytes, nonce: bytes, ciphertext_and_tag: bytes, aad: Optional[bytes] = None) -> bytes:
    """
    Decrypts and verifies ciphertext with AES-256-GCM.
    Raises CorruptedCiphertextError if authentication tag fails or data was tampered with.
    """
    if len(key) != 32:
        raise CryptoError("AES-256 key must be exactly 32 bytes.")
    if len(nonce) != 12:
        raise CryptoError("AES-GCM nonce must be exactly 12 bytes.")
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext_and_tag, aad)
    except InvalidTag:
        raise CorruptedCiphertextError(
            "Authentication tag verification failed: ciphertext is corrupt, tampered with, or invalid key."
        )


# -----------------------------------------------------------------------------
# Recovery Key Helpers (Formatted Base32/Alphanumeric grouping)
# -----------------------------------------------------------------------------

def format_recovery_key(key_bytes: bytes) -> str:
    """
    Formats a 32-byte recovery key into 8 groups of 4 uppercase alphanumeric characters:
    e.g., 'A1B2-C3D4-E5F6-G7H8-J9K0-L1M2-N3P4-Q5R6'
    """
    hex_str = key_bytes.hex().upper()
    return "-".join(hex_str[i:i + 4] for i in range(0, min(len(hex_str), 32), 4))


def parse_recovery_key(recovery_str: str) -> bytes:
    """Parses and validates a recovery key string back into 16 or 32 bytes."""
    cleaned = re.sub(r'[^A-Fa-f0-9]', '', recovery_str).lower()
    if len(cleaned) not in (32, 64):
        raise CryptoError("Invalid recovery key format. Expected 32 or 64 hex characters.")
    return bytes.fromhex(cleaned)


# -----------------------------------------------------------------------------
# Vault Key Envelope Management
# -----------------------------------------------------------------------------

class VaultEnvelope:
    """
    Manages the stored envelope containing the wrapped Data Encryption Key (DEK).
    Stores:
    - Argon2id salt & parameters
    - DEK wrapped with Password KEK
    - DEK wrapped with Recovery KEK
    """

    def __init__(self, envelope_path: Optional[Path] = None):
        self.envelope_path = envelope_path or (settings.DATA_DIR / "security" / "vault_envelope.json")
        self.envelope_path.parent.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.envelope_path.exists()

    def initialize_vault(self, password: str) -> Tuple[bytes, str]:
        """
        Creates a new cryptographically random 256-bit DEK,
        derives password KEK and recovery KEK,
        wraps DEK in both envelopes, and persists the envelope file.
        Returns (dek_bytes, formatted_recovery_key).
        """
        if self.exists():
            raise CryptoError("Vault is already initialized.")

        # 1. Generate random 256-bit DEK
        dek = secrets.token_bytes(32)

        # 2. Derive Password KEK
        pwd_salt = secrets.token_bytes(16)
        pwd_kek = derive_key_argon2id(password, pwd_salt)
        pwd_nonce, pwd_wrapped = encrypt_aes_gcm(pwd_kek, dek, aad=b"DA_VAULT_DEK_V1")

        # 3. Generate random 256-bit Recovery Key and derive Recovery KEK
        rec_bytes = secrets.token_bytes(16)  # 128-bit entropy displayed as 32 hex chars
        rec_salt = secrets.token_bytes(16)
        rec_kek = derive_key_argon2id(rec_bytes.hex(), rec_salt)
        rec_nonce, rec_wrapped = encrypt_aes_gcm(rec_kek, dek, aad=b"DA_VAULT_REC_V1")

        envelope_data = {
            "version": 1,
            "kdf": "Argon2id",
            "kdf_params": {
                "time_cost": ARGON2_TIME_COST,
                "memory_cost": ARGON2_MEMORY_COST,
                "parallelism": ARGON2_PARALLELISM,
                "salt_hex": pwd_salt.hex(),
            },
            "password_wrapped_dek": {
                "nonce_hex": pwd_nonce.hex(),
                "ciphertext_hex": pwd_wrapped.hex(),
            },
            "recovery_kdf_params": {
                "time_cost": ARGON2_TIME_COST,
                "memory_cost": ARGON2_MEMORY_COST,
                "parallelism": ARGON2_PARALLELISM,
                "salt_hex": rec_salt.hex(),
            },
            "recovery_wrapped_dek": {
                "nonce_hex": rec_nonce.hex(),
                "ciphertext_hex": rec_wrapped.hex(),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Write safely with atomic replacement
        temp_path = self.envelope_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(envelope_data, indent=2), encoding="utf-8")
        temp_path.replace(self.envelope_path)

        formatted_rec_key = format_recovery_key(rec_bytes)
        logger.info("Vault envelope initialized successfully with AES-256-GCM and Argon2id.")
        return dek, formatted_rec_key

    def unwrap_dek_with_password(self, password: str) -> bytes:
        """Derives KEK from password and unwraps DEK. Raises InvalidPasswordError on failure."""
        if not self.exists():
            raise CryptoError("Vault is not initialized.")

        try:
            data = json.loads(self.envelope_path.read_text(encoding="utf-8"))
            kdf_p = data["kdf_params"]
            salt = bytes.fromhex(kdf_p["salt_hex"])
            pwd_kek = derive_key_argon2id(
                password,
                salt,
                time_cost=kdf_p["time_cost"],
                memory_cost=kdf_p["memory_cost"],
                parallelism=kdf_p["parallelism"]
            )
            wrapped = data["password_wrapped_dek"]
            nonce = bytes.fromhex(wrapped["nonce_hex"])
            ciphertext = bytes.fromhex(wrapped["ciphertext_hex"])
            return decrypt_aes_gcm(pwd_kek, nonce, ciphertext, aad=b"DA_VAULT_DEK_V1")
        except CorruptedCiphertextError:
            raise InvalidPasswordError("Incorrect vault passphrase.")
        except Exception as e:
            if isinstance(e, InvalidPasswordError):
                raise
            raise CryptoError(f"Failed to read vault envelope: {e}")

    def unwrap_dek_with_recovery_key(self, recovery_key: str) -> bytes:
        """Unwraps DEK using the recovery key. Raises InvalidPasswordError on failure."""
        if not self.exists():
            raise CryptoError("Vault is not initialized.")

        try:
            rec_bytes = parse_recovery_key(recovery_key)
            data = json.loads(self.envelope_path.read_text(encoding="utf-8"))
            kdf_p = data["recovery_kdf_params"]
            salt = bytes.fromhex(kdf_p["salt_hex"])
            rec_kek = derive_key_argon2id(
                rec_bytes.hex(),
                salt,
                time_cost=kdf_p["time_cost"],
                memory_cost=kdf_p["memory_cost"],
                parallelism=kdf_p["parallelism"]
            )
            wrapped = data["recovery_wrapped_dek"]
            nonce = bytes.fromhex(wrapped["nonce_hex"])
            ciphertext = bytes.fromhex(wrapped["ciphertext_hex"])
            return decrypt_aes_gcm(rec_kek, nonce, ciphertext, aad=b"DA_VAULT_REC_V1")
        except CorruptedCiphertextError:
            raise InvalidPasswordError("Invalid recovery key.")
        except Exception as e:
            if isinstance(e, InvalidPasswordError):
                raise
            raise CryptoError(f"Recovery key processing failed: {e}")

    def rewrap_dek_with_new_password(self, current_password: str, new_password: str) -> None:
        """
        Changes vault password by unwrapping DEK with old password and re-wrapping with new KEK.
        Does NOT re-encrypt memories on disk!
        """
        dek = self.unwrap_dek_with_password(current_password)

        new_salt = secrets.token_bytes(16)
        new_kek = derive_key_argon2id(new_password, new_salt)
        new_nonce, new_wrapped = encrypt_aes_gcm(new_kek, dek, aad=b"DA_VAULT_DEK_V1")

        data = json.loads(self.envelope_path.read_text(encoding="utf-8"))
        data["kdf_params"]["salt_hex"] = new_salt.hex()
        data["password_wrapped_dek"]["nonce_hex"] = new_nonce.hex()
        data["password_wrapped_dek"]["ciphertext_hex"] = new_wrapped.hex()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        temp_path = self.envelope_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(self.envelope_path)
        logger.info("Vault master password changed and DEK re-wrapped successfully.")

    def reset_password_with_recovery_key(self, recovery_key: str, new_password: str) -> None:
        """Resets the vault password using a valid recovery key."""
        dek = self.unwrap_dek_with_recovery_key(recovery_key)

        new_salt = secrets.token_bytes(16)
        new_kek = derive_key_argon2id(new_password, new_salt)
        new_nonce, new_wrapped = encrypt_aes_gcm(new_kek, dek, aad=b"DA_VAULT_DEK_V1")

        data = json.loads(self.envelope_path.read_text(encoding="utf-8"))
        data["kdf_params"]["salt_hex"] = new_salt.hex()
        data["password_wrapped_dek"]["nonce_hex"] = new_nonce.hex()
        data["password_wrapped_dek"]["ciphertext_hex"] = new_wrapped.hex()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        temp_path = self.envelope_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(self.envelope_path)
        logger.info("Vault password recovered and updated via recovery key.")


# -----------------------------------------------------------------------------
# In-Memory Vault Key Manager (Singleton Lifecycle)
# -----------------------------------------------------------------------------

class VaultKeyManager:
    """
    Manages in-memory DEK reference.
    Guarantees keys remain in RAM only while unlocked and zeroes references on lock/shutdown.
    Supports singleton usage or isolated instances for testing via envelope_path.
    """
    _instance: Optional['VaultKeyManager'] = None

    def __new__(cls, envelope_path: Optional[Path] = None) -> 'VaultKeyManager':
        if envelope_path is not None:
            obj = super().__new__(cls)
            obj._init_state(envelope_path)
            return obj
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state(None)
        return cls._instance

    def _init_state(self, envelope_path: Optional[Path] = None) -> None:
        self._dek: Optional[bytearray] = None
        self._is_unlocked: bool = False
        self._envelope = VaultEnvelope(envelope_path)
        self._auto_lock_minutes: int = 15
        self._last_activity: float = datetime.now(timezone.utc).timestamp()

    @property
    def envelope(self) -> VaultEnvelope:
        return self._envelope

    def is_initialized(self) -> bool:
        return self._envelope.exists()

    @property
    def is_unlocked_state(self) -> bool:
        return self._is_unlocked

    def check_auto_lock(self) -> bool:
        """Checks auto-lock timeout. Returns True if vault was auto-locked."""
        if self._is_unlocked and self._auto_lock_minutes > 0:
            now = datetime.now(timezone.utc).timestamp()
            if now - self._last_activity > (self._auto_lock_minutes * 60):
                logger.info("Auto-lock timeout reached. Locking vault.")
                self.lock()
                return True
        return False

    def is_unlocked(self) -> bool:
        if self.check_auto_lock():
            return False
        return self._is_unlocked

    def record_activity(self) -> None:
        """Updates last activity timestamp to prevent premature auto-lock."""
        self._last_activity = datetime.now(timezone.utc).timestamp()

    def set_auto_lock_minutes(self, minutes: int) -> None:
        self._auto_lock_minutes = max(1, minutes)

    def setup_vault(self, password: str, auto_lock_minutes: int = 15) -> str:
        """Initializes a new vault with passphrase and unlocks it immediately."""
        dek_bytes, recovery_key = self._envelope.initialize_vault(password)
        self._dek = bytearray(dek_bytes)
        self._is_unlocked = True
        self._auto_lock_minutes = auto_lock_minutes
        self.record_activity()
        return recovery_key

    def unlock_with_password(self, password: str) -> bool:
        """Unlocks the vault with password."""
        dek_bytes = self._envelope.unwrap_dek_with_password(password)
        self._dek = bytearray(dek_bytes)
        self._is_unlocked = True
        self.record_activity()
        logger.info("Vault unlocked successfully with password.")
        return True

    def unlock_with_recovery_key(self, recovery_key: str) -> bool:
        """Unlocks the vault with recovery key."""
        dek_bytes = self._envelope.unwrap_dek_with_recovery_key(recovery_key)
        self._dek = bytearray(dek_bytes)
        self._is_unlocked = True
        self.record_activity()
        logger.info("Vault unlocked successfully with recovery key.")
        return True

    def change_password(self, current_password: str, new_password: str) -> None:
        """Changes vault password by re-wrapping DEK."""
        self._envelope.rewrap_dek_with_new_password(current_password, new_password)
        self.record_activity()

    def recover_with_recovery_key(self, recovery_key: str, new_password: str) -> None:
        """Recovers and updates vault password using recovery key."""
        self._envelope.reset_password_with_recovery_key(recovery_key, new_password)
        self.record_activity()

    def lock(self) -> None:
        """Explicitly locks the vault and zeroes the in-memory DEK."""
        if self._dek is not None:
            # Overwrite memory buffer with zeros before deletion
            for i in range(len(self._dek)):
                self._dek[i] = 0
            self._dek = None
        self._is_unlocked = False
        logger.info("Vault locked. Memory keys zeroed.")

    def get_dek(self) -> bytes:
        """Returns the in-memory DEK if unlocked; raises VaultLockedError otherwise."""
        if not self.is_unlocked() or self._dek is None:
            raise VaultLockedError("Vault is locked. Passphrase required to access encrypted memories.")
        self.record_activity()
        return bytes(self._dek)


vault_key_manager = VaultKeyManager()
