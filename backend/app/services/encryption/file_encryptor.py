"""
Authenticated Streaming Chunked File Encryptor for Digital Afterlife.
Phase 6: AES-256-GCM chunked file encryption supporting large media (videos, audio, photos, documents)
with memory-bounded streaming (64 KB RAM footprint), unique nonces, and cryptographic tamper detection.
"""
import io
import os
import secrets
from pathlib import Path
from typing import Generator, BinaryIO, Union, Optional, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from backend.app.core.crypto import (
    CryptoError,
    CorruptedCiphertextError,
)
from backend.app.core.logging import logger

MAGIC_HEADER = b"DAENC1"
FORMAT_VERSION = 1
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB
HEADER_SIZE = 40  # 6 (magic) + 2 (ver) + 4 (chunk_size) + 16 (salt) + 12 (base_nonce)


def derive_chunk_nonce(base_nonce: bytes, chunk_index: int) -> bytes:
    """
    Derives a cryptographically unique 12-byte nonce for a specific chunk index.
    Combines the random 12-byte base nonce with the chunk index.
    """
    prefix = base_nonce[:8]
    counter_part = int.from_bytes(base_nonce[8:], "big") ^ (chunk_index & 0xFFFFFFFF)
    return prefix + counter_part.to_bytes(4, "big")


def make_aad(chunk_index: int, is_last: bool) -> bytes:
    """
    Constructs Additional Authenticated Data (AAD) binding format, chunk order, and EOF status.
    Prevents chunk reordering, truncation, splicing, or insertion attacks.
    """
    return MAGIC_HEADER + chunk_index.to_bytes(8, "big") + (b"\x01" if is_last else b"\x00")


class FileEncryptor:
    """
    Encrypts and decrypts files using authenticated AES-256-GCM chunking.
    Memory footprint is bounded to ~64 KB regardless of file size.
    """

    def __init__(self, key_manager: Optional[Any] = None):
        self.key_manager = key_manager

    def _resolve_dek(self, dek: Optional[bytes] = None) -> bytes:
        if dek is not None:
            return dek
        if self.key_manager is not None:
            return self.key_manager.get_dek()
        from backend.app.core.crypto import vault_key_manager
        return vault_key_manager.get_dek()

    @staticmethod
    def is_encrypted_file(file_path: Union[str, Path]) -> bool:
        """Inspects first 6 bytes of a file on disk to determine if it is encrypted."""
        p = Path(file_path)
        if not p.exists() or p.stat().st_size < HEADER_SIZE:
            return False
        try:
            with open(p, "rb") as f:
                header = f.read(len(MAGIC_HEADER))
                return header == MAGIC_HEADER
        except Exception:
            return False

    @staticmethod
    def is_encrypted_bytes(data: bytes) -> bool:
        """Inspects byte buffer to check for magic header."""
        return len(data) >= HEADER_SIZE and data.startswith(MAGIC_HEADER)

    def encrypt_stream(
        self,
        in_stream: BinaryIO,
        out_stream: BinaryIO,
        dek: Optional[bytes] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> int:
        """
        Encrypts an open input binary stream and writes to an open output binary stream.
        Returns total bytes written.
        """
        resolved_dek = self._resolve_dek(dek)
        if len(resolved_dek) != 32:
            raise CryptoError("DEK must be exactly 32 bytes for AES-256-GCM.")

        aesgcm = AESGCM(resolved_dek)
        file_salt = secrets.token_bytes(16)
        base_nonce = secrets.token_bytes(12)

        # Write 40-byte header
        out_stream.write(MAGIC_HEADER)
        out_stream.write(FORMAT_VERSION.to_bytes(2, "big"))
        out_stream.write(chunk_size.to_bytes(4, "big"))
        out_stream.write(file_salt)
        out_stream.write(base_nonce)

        bytes_written = HEADER_SIZE
        chunk_index = 0

        # Read ahead one chunk to accurately identify the last chunk
        current_chunk = in_stream.read(chunk_size)
        while current_chunk:
            next_chunk = in_stream.read(chunk_size)
            is_last = len(next_chunk) == 0

            nonce = derive_chunk_nonce(base_nonce, chunk_index)
            aad = make_aad(chunk_index, is_last)
            encrypted_chunk = aesgcm.encrypt(nonce, current_chunk, aad)

            # Write chunk length (4 bytes) + encrypted payload (with 16-byte tag)
            enc_len = len(encrypted_chunk)
            out_stream.write(enc_len.to_bytes(4, "big"))
            out_stream.write(encrypted_chunk)

            bytes_written += 4 + enc_len
            chunk_index += 1
            current_chunk = next_chunk

        # Edge case: 0-byte empty file
        if chunk_index == 0:
            nonce = derive_chunk_nonce(base_nonce, 0)
            aad = make_aad(0, True)
            encrypted_chunk = aesgcm.encrypt(nonce, b"", aad)
            enc_len = len(encrypted_chunk)
            out_stream.write(enc_len.to_bytes(4, "big"))
            out_stream.write(encrypted_chunk)
            bytes_written += 4 + enc_len

        return bytes_written

    def decrypt_stream(self, in_stream: BinaryIO, dek: Optional[bytes] = None) -> Generator[bytes, None, None]:
        """
        Decrypts an encrypted binary stream and yields plaintext chunks.
        Raises CorruptedCiphertextError if authentication tag verification fails.
        """
        resolved_dek = self._resolve_dek(dek)
        if len(resolved_dek) != 32:
            raise CryptoError("DEK must be exactly 32 bytes for AES-256-GCM.")

        header = in_stream.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise CorruptedCiphertextError("Truncated encryption header.")

        magic = header[:6]
        if magic != MAGIC_HEADER:
            raise CorruptedCiphertextError(f"Invalid file magic header: expected {MAGIC_HEADER}, got {magic}.")

        version = int.from_bytes(header[6:8], "big")
        if version != FORMAT_VERSION:
            raise CorruptedCiphertextError(f"Unsupported encryption format version: {version}.")

        chunk_size = int.from_bytes(header[8:12], "big")
        # salt = header[12:28]
        base_nonce = header[28:40]

        aesgcm = AESGCM(resolved_dek)
        chunk_index = 0
        saw_last_chunk = False

        while True:
            len_bytes = in_stream.read(4)
            if not len_bytes:
                break

            if len(len_bytes) < 4:
                raise CorruptedCiphertextError("Truncated chunk length indicator.")

            chunk_len = int.from_bytes(len_bytes, "big")
            encrypted_data = in_stream.read(chunk_len)
            if len(encrypted_data) < chunk_len:
                raise CorruptedCiphertextError(
                    f"Unexpected EOF reading encrypted chunk {chunk_index}. Expected {chunk_len} bytes."
                )

            nonce = derive_chunk_nonce(base_nonce, chunk_index)

            # Try decrypting as non-last first; if tag fails, try decrypting as last chunk
            plaintext = None
            for is_last in (False, True):
                aad = make_aad(chunk_index, is_last)
                try:
                    plaintext = aesgcm.decrypt(nonce, encrypted_data, aad)
                    if is_last:
                        saw_last_chunk = True
                    break
                except InvalidTag:
                    continue

            if plaintext is None:
                raise CorruptedCiphertextError(
                    f"Authentication verification failed at chunk {chunk_index}. Data is corrupted or tampered."
                )

            yield plaintext
            chunk_index += 1

            if saw_last_chunk:
                break

        if not saw_last_chunk and chunk_index > 0:
            raise CorruptedCiphertextError("Stream ended prematurely without end-of-file chunk marker.")

    def encrypt_bytes(self, plaintext: bytes, dek: Optional[bytes] = None) -> bytes:
        """Encrypts an in-memory byte buffer into encrypted bytes."""
        in_buf = io.BytesIO(plaintext)
        out_buf = io.BytesIO()
        self.encrypt_stream(in_buf, out_buf, dek)
        return out_buf.getvalue()

    def decrypt_bytes(self, ciphertext: bytes, dek: Optional[bytes] = None) -> bytes:
        """Decrypts an encrypted byte buffer into plaintext bytes."""
        in_buf = io.BytesIO(ciphertext)
        decrypted_parts = []
        for chunk in self.decrypt_stream(in_buf, dek):
            decrypted_parts.append(chunk)
        return b"".join(decrypted_parts)

    def encrypt_file_on_disk(
        self,
        source_path: Path,
        dest_path: Path,
        dek: Optional[bytes] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> int:
        """Encrypts file from source_path to dest_path safely."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(source_path, "rb") as fin, open(dest_path, "wb") as fout:
            return self.encrypt_stream(fin, fout, dek, chunk_size=chunk_size)

    def decrypt_file_on_disk(self, source_path: Path, dest_path: Path, dek: Optional[bytes] = None) -> None:
        """Decrypts file from source_path to dest_path safely."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(source_path, "rb") as fin, open(dest_path, "wb") as fout:
            for chunk in self.decrypt_stream(fin, dek):
                fout.write(chunk)


file_encryptor = FileEncryptor()
