"""
Field-Level Authenticated Encryption for SQLite sensitive data.
Phase 6: Protects sensitive extracted text, speech transcripts, speaker embeddings,
notes, and generated biographies at rest.
"""
import base64
from typing import Optional, Union

from backend.app.core.crypto import (
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    vault_key_manager,
    VaultLockedError,
    CryptoError,
)
from backend.app.core.logging import logger

FIELD_ENC_PREFIX = "ENC:v1:"


def is_encrypted_field(val: Optional[str]) -> bool:
    """Checks whether a string field contains an encrypted ciphertext envelope."""
    return bool(val and isinstance(val, str) and val.startswith(FIELD_ENC_PREFIX))


def encrypt_field(text: Optional[str], dek: Optional[bytes] = None) -> Optional[str]:
    """
    Encrypts a text string using AES-256-GCM.
    Returns 'ENC:v1:<base64_encoded_nonce_and_ciphertext>'.
    """
    if text is None or not text:
        return text

    if is_encrypted_field(text):
        return text  # Already encrypted

    if dek is None:
        if not vault_key_manager.is_initialized() or not vault_key_manager.is_unlocked():
            return text
        dek = vault_key_manager.get_dek()

    nonce, ciphertext_and_tag = encrypt_aes_gcm(dek, text.encode("utf-8"), aad=b"DA_FIELD_V1")
    payload = nonce + ciphertext_and_tag
    encoded = base64.urlsafe_b64encode(payload).decode("ascii")
    return f"{FIELD_ENC_PREFIX}{encoded}"


def decrypt_field(
    ciphertext: Optional[str],
    dek: Optional[bytes] = None,
    strict: bool = False
) -> Optional[str]:
    """
    Decrypts an encrypted field envelope.
    If unencrypted (legacy plaintext), returns as-is.
    If locked and strict=True, raises VaultLockedError.
    If locked and strict=False, returns '[Vault Locked — Decryption Required]'.
    """
    if ciphertext is None or not ciphertext:
        return ciphertext

    if not is_encrypted_field(ciphertext):
        if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
            if strict:
                raise VaultLockedError("Vault is locked. Passphrase required to access sensitive records.")
            return "[Vault Locked — Decryption Required]"
        return ciphertext  # Legacy plaintext before vault setup or when unlocked

    if dek is None:
        try:
            dek = vault_key_manager.get_dek()
        except VaultLockedError:
            if strict:
                raise
            return "[Vault Locked — Decryption Required]"

    try:
        raw_b64 = ciphertext[len(FIELD_ENC_PREFIX):]
        payload = base64.urlsafe_b64decode(raw_b64)
        if len(payload) < 28:  # 12-byte nonce + 16-byte tag minimum
            raise CryptoError("Corrupted field payload length.")
        nonce = payload[:12]
        ct = payload[12:]
        decrypted_bytes = decrypt_aes_gcm(dek, nonce, ct, aad=b"DA_FIELD_V1")
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decrypt field envelope: {e}")
        if strict:
            raise
        return "[Corrupted Encrypted Field]"

