"""
Safe Migration and Encrypted Backup Service.
Phase 6: Verifiable file migration, pre-migration plaintext backups,
SHA-256 integrity verification, instant rollback, and encrypted full-archive backups.
"""
import io
import os
import shutil
import zipfile
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.crypto import (
    vault_key_manager,
    VaultLockedError,
    CryptoError,
)
from backend.app.core.security import compute_sha256
from backend.app.services.encryption.file_encryptor import file_encryptor


class MigrationStatus:
    def __init__(self):
        self.is_running: bool = False
        self.total_files: int = 0
        self.processed_files: int = 0
        self.successful_files: int = 0
        self.failed_files: int = 0
        self.errors: List[str] = []
        self.cancelled: bool = False
        self.completed_at: Optional[str] = None
        self.backup_path: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        return self.to_dict()[item]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "progress_percent": round((self.processed_files / self.total_files * 100), 1) if self.total_files > 0 else 0,
            "errors": self.errors[-10:],
            "cancelled": self.cancelled,
            "completed_at": self.completed_at,
            "backup_path": self.backup_path,
        }


class MigrationService:
    def __init__(
        self,
        key_manager: Optional[Any] = None,
        file_encryptor: Optional[Any] = None,
        storage_dirs: Optional[List[Path]] = None,
        backup_root: Optional[Path] = None,
    ):
        self.status = MigrationStatus()
        self._lock = threading.Lock()
        self._key_manager = key_manager
        self._file_encryptor = file_encryptor
        self._storage_dirs = storage_dirs
        self._backup_root = backup_root

    @property
    def key_manager(self):
        if self._key_manager is not None:
            return self._key_manager
        from backend.app.core.crypto import vault_key_manager
        return vault_key_manager

    @property
    def encryptor(self):
        if self._file_encryptor is not None:
            return self._file_encryptor
        from backend.app.services.encryption.file_encryptor import file_encryptor
        return file_encryptor

    def get_storage_dirs(self) -> List[Path]:
        if self._storage_dirs is not None:
            return [Path(d) for d in self._storage_dirs]
        return [settings.STORAGE_DIR, settings.DATA_DIR / "thumbnails"]

    def get_backup_dir(self) -> Path:
        if self._backup_root is not None:
            return Path(self._backup_root) / "pre_migration"
        return settings.DATA_DIR / "backups" / "pre_migration"

    def scan_files(self) -> Dict[str, Any]:
        """Scans storage and thumbnail directories to count plaintext and encrypted files."""
        plaintext_files: List[Path] = []
        encrypted_files: List[Path] = []

        for d in self.get_storage_dirs():
            if not d.exists():
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    p = Path(root) / f
                    if f.endswith((".enc_staging", ".bak", ".tmp")):
                        continue
                    if self.encryptor.is_encrypted_file(p):
                        encrypted_files.append(p)
                    else:
                        plaintext_files.append(p)

        return {
            "total_files": len(plaintext_files) + len(encrypted_files),
            "plaintext_count": len(plaintext_files),
            "encrypted_count": len(encrypted_files),
            "is_fully_encrypted": len(plaintext_files) == 0 and len(encrypted_files) > 0,
            "plaintext_files": [str(p) for p in plaintext_files],
        }

    def start_migration(self, background: bool = True, sync: bool = False) -> MigrationStatus:
        """
        Starts safe file encryption migration.
        Guarantees:
        1. Backups preserved before writing.
        2. Encrypts to temporary staging file.
        3. Decrypts staging file and verifies exact SHA-256 digest match against original.
        4. Replaces original with verified encrypted file atomically.
        """
        if sync:
            background = False

        if not self.key_manager.is_unlocked():
            raise VaultLockedError("Vault must be unlocked to start file migration.")

        with self._lock:
            if self.status.is_running:
                return self.status

            self.status = MigrationStatus()
            self.status.is_running = True

        if background:
            t = threading.Thread(target=self._run_migration, daemon=True)
            t.start()
            return self.status
        else:
            self._run_migration()
            return self.status

    def cancel_migration(self) -> None:
        """Requests cancellation of active migration."""
        self.status.cancelled = True

    def _run_migration(self) -> None:
        try:
            dek = self.key_manager.get_dek()
            scan_res = self.scan_files()
            plaintext_paths = [Path(p) for p in scan_res["plaintext_files"]]

            self.status.total_files = len(plaintext_paths)
            if self.status.total_files == 0:
                self.status.is_running = False
                self.status.completed_at = datetime.now(timezone.utc).isoformat()
                return

            # Prepare pre-migration backup directory
            backup_dir = self.get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.status.backup_path = str(backup_dir)

            for p in plaintext_paths:
                if self.status.cancelled:
                    logger.info("File migration was cancelled by user.")
                    break

                try:
                    self._migrate_single_file(p, dek, backup_dir)
                    self.status.successful_files += 1
                except Exception as e:
                    logger.error(f"Failed to migrate file {p.name}: {e}")
                    self.status.failed_files += 1
                    self.status.errors.append(f"{p.name}: {str(e)}")
                finally:
                    self.status.processed_files += 1

            # Migrate database records
            if not self.status.cancelled:
                self._migrate_database_records(dek)

        finally:
            self.status.is_running = False
            self.status.completed_at = datetime.now(timezone.utc).isoformat()

    def _migrate_database_records(self, dek: bytes, db: Optional[Any] = None) -> int:
        """Encrypts sensitive database fields that are still in plaintext."""
        try:
            from backend.app.models.memory import Memory
            from backend.app.models.transcript import Transcript, TranscriptSegment
            from backend.app.models.storytelling import StoryArtifact, RemembrancePage
            from backend.app.services.encryption.field_cipher import encrypt_field, is_encrypted_field

            own_session = False
            if db is None:
                from backend.app.database.session import SessionLocal
                db = SessionLocal()
                own_session = True

            migrated_count = 0
            try:
                # 1. Memories
                for mem in db.query(Memory).all():
                    changed = False
                    if mem.description and not is_encrypted_field(mem.description):
                        mem.description = encrypt_field(mem.description, dek=dek)
                        changed = True
                        migrated_count += 1
                    if mem.extracted_text and not is_encrypted_field(mem.extracted_text):
                        mem.extracted_text = encrypt_field(mem.extracted_text, dek=dek)
                        changed = True
                        migrated_count += 1
                    if changed:
                        db.add(mem)

                # 2. Transcripts
                for tr in db.query(Transcript).all():
                    if tr.transcript_text and not is_encrypted_field(tr.transcript_text):
                        tr.transcript_text = encrypt_field(tr.transcript_text, dek=dek)
                        db.add(tr)
                        migrated_count += 1

                for seg in db.query(TranscriptSegment).all():
                    if seg.text and not is_encrypted_field(seg.text):
                        seg.text = encrypt_field(seg.text, dek=dek)
                        db.add(seg)
                        migrated_count += 1

                # 3. Story Artifacts & Remembrance
                for art in db.query(StoryArtifact).all():
                    if art.content and not is_encrypted_field(art.content):
                        art.content = encrypt_field(art.content, dek=dek)
                        db.add(art)
                        migrated_count += 1

                for rp in db.query(RemembrancePage).all():
                    if rp.user_personal_notes and not is_encrypted_field(rp.user_personal_notes):
                        rp.user_personal_notes = encrypt_field(rp.user_personal_notes, dek=dek)
                        db.add(rp)
                        migrated_count += 1

                db.commit()
                logger.info(f"Database migration completed: encrypted {migrated_count} sensitive fields.")
                return migrated_count
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to migrate database fields: {e}")
                return 0
            finally:
                if own_session:
                    db.close()
        except Exception as e:
            logger.debug(f"Database migration skipped: {e}")
            return 0

    def _migrate_single_file(self, file_path: Path, dek: bytes, backup_dir: Path) -> None:
        """Migrates a single file safely with hash verification and backup."""
        if self.encryptor.is_encrypted_file(file_path):
            return  # Already encrypted

        # 1. Read original bytes and compute SHA-256
        orig_bytes = file_path.read_bytes()
        orig_hash = compute_sha256(orig_bytes)

        # 2. Preserve backup copy
        rel_path = file_path.name
        backup_file = backup_dir / rel_path
        if not backup_file.exists():
            backup_file.write_bytes(orig_bytes)

        # 3. Encrypt to staging destination
        staging_path = file_path.with_suffix(f"{file_path.suffix}.enc_staging")
        self.encryptor.encrypt_file_on_disk(file_path, staging_path, dek)

        # 4. Verify encrypted output can be decrypted and matches original SHA-256
        with open(staging_path, "rb") as fin:
            decrypted_chunks = list(self.encryptor.decrypt_stream(fin, dek))
            decrypted_content = b"".join(decrypted_chunks)
            decrypted_hash = compute_sha256(decrypted_content)

            if decrypted_hash != orig_hash:
                staging_path.unlink(missing_ok=True)
                raise CryptoError(
                    f"Integrity check failed: decrypted hash {decrypted_hash} does not match original {orig_hash}."
                )

        # 5. Commit: atomically replace original with verified encrypted staging file
        staging_path.replace(file_path)
        logger.info(f"Successfully migrated and verified encrypted file: {file_path.name}")

    def rollback_migration(self) -> Dict[str, Any]:
        """
        Restores plaintext files from the pre-migration backup directory.
        """
        backup_dir = self.get_backup_dir()
        if not backup_dir.exists():
            raise CryptoError("No pre-migration backup directory found for rollback.")

        restored_count = 0
        search_dirs = self.get_storage_dirs()

        for backup_file in backup_dir.iterdir():
            if backup_file.is_file():
                target_path = None
                for base in search_dirs:
                    for root, _, files in os.walk(base):
                        if backup_file.name in files:
                            target_path = Path(root) / backup_file.name
                            break
                    if target_path:
                        break

                if target_path:
                    shutil.copy2(backup_file, target_path)
                    restored_count += 1

        # Rollback database records if any
        restored_fields = self._rollback_database_records()

        logger.info(f"Rollback completed: restored {restored_count} files and {restored_fields} database fields from backup.")
        return {
            "status": "success",
            "restored_files": restored_count,
            "restored_files_count": restored_count,
            "restored_fields_count": restored_fields
        }

    def _rollback_database_records(self, db: Optional[Any] = None) -> int:
        """Restores encrypted database fields back to plaintext using unlocked DEK."""
        try:
            if not self.key_manager.is_unlocked():
                return 0
            dek = self.key_manager.get_dek()
            from backend.app.models.memory import Memory
            from backend.app.models.transcript import Transcript, TranscriptSegment
            from backend.app.models.storytelling import StoryArtifact, RemembrancePage
            from backend.app.services.encryption.field_cipher import decrypt_field, is_encrypted_field

            own_session = False
            if db is None:
                from backend.app.database.session import SessionLocal
                db = SessionLocal()
                own_session = True

            restored_fields_count = 0
            try:
                for mem in db.query(Memory).all():
                    changed = False
                    if is_encrypted_field(mem.description):
                        mem.description = decrypt_field(mem.description, dek=dek)
                        changed = True
                        restored_fields_count += 1
                    if is_encrypted_field(mem.extracted_text):
                        mem.extracted_text = decrypt_field(mem.extracted_text, dek=dek)
                        changed = True
                        restored_fields_count += 1
                    if changed:
                        db.add(mem)

                for tr in db.query(Transcript).all():
                    if is_encrypted_field(tr.transcript_text):
                        tr.transcript_text = decrypt_field(tr.transcript_text, dek=dek)
                        db.add(tr)
                        restored_fields_count += 1

                for seg in db.query(TranscriptSegment).all():
                    if is_encrypted_field(seg.text):
                        seg.text = decrypt_field(seg.text, dek=dek)
                        db.add(seg)
                        restored_fields_count += 1

                for art in db.query(StoryArtifact).all():
                    if is_encrypted_field(art.content):
                        art.content = decrypt_field(art.content, dek=dek)
                        db.add(art)
                        restored_fields_count += 1

                for rp in db.query(RemembrancePage).all():
                    if is_encrypted_field(rp.user_personal_notes):
                        rp.user_personal_notes = decrypt_field(rp.user_personal_notes, dek=dek)
                        db.add(rp)
                        restored_fields_count += 1

                db.commit()
                logger.info(f"Database rollback completed: decrypted {restored_fields_count} fields to plaintext.")
                return restored_fields_count
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to rollback database fields: {e}")
                return 0
            finally:
                if own_session:
                    db.close()
        except Exception as e:
            logger.debug(f"Database rollback skipped: {e}")
            return 0

    # -------------------------------------------------------------------------
    # Encrypted Backup & Restore
    # -------------------------------------------------------------------------

    def create_encrypted_backup(
        self,
        dest_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
        out_dir: Optional[Path] = None
    ) -> Path:
        """
        Creates a single authenticated, encrypted backup archive (.da-backup)
        containing the database, keystore envelope, and all stored media.
        """
        dek = self.key_manager.get_dek()
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if dest_path:
            backup_path = dest_path
        elif out_dir:
            backup_path = Path(out_dir) / f"vault_backup_{now_str}.da-backup"
        else:
            backup_path = settings.DATA_DIR / "backups" / f"vault_backup_{now_str}.da-backup"

        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Create in-memory zip of database and files
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add SQLite DB
            database_file = db_path or (settings.DATABASE_PATH if settings.DATABASE_PATH.exists() else Path("data/digital_afterlife.db"))
            if database_file.exists():
                zf.write(database_file, arcname="digital_afterlife.db")

            # Add vault envelope
            env_file = self.key_manager.envelope.envelope_path
            if env_file.exists():
                zf.write(env_file, arcname="vault_envelope.json")

            # Add media storage files
            for base_dir in self.get_storage_dirs():
                if not base_dir.exists():
                    continue
                for root, _, files in os.walk(base_dir):
                    for f in files:
                        p = Path(root) / f
                        arcname = Path("memories") / p.relative_to(base_dir)
                        zf.write(p, arcname=str(arcname))

        zip_bytes = zip_buf.getvalue()

        # 2. Encrypt zip archive using AES-256-GCM chunking
        enc_bytes = self.encryptor.encrypt_bytes(zip_bytes, dek)
        backup_path.write_bytes(enc_bytes)
        logger.info(f"Created encrypted vault backup: {backup_path.name} ({len(enc_bytes)} bytes)")
        return backup_path

    def restore_encrypted_backup(self, backup_path: Path, target_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Restores an encrypted backup archive after verifying its cryptographic integrity.
        """
        dek = self.key_manager.get_dek()
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file '{backup_path}' does not exist.")

        enc_bytes = backup_path.read_bytes()
        # Verify and decrypt
        zip_bytes = self.encryptor.decrypt_bytes(enc_bytes, dek)

        restore_root = target_dir or settings.DATA_DIR

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            # Extract database if present
            if "digital_afterlife.db" in zf.namelist():
                db_data = zf.read("digital_afterlife.db")
                dest_db = (restore_root / "digital_afterlife.db") if target_dir else settings.DATABASE_PATH
                dest_db.parent.mkdir(parents=True, exist_ok=True)
                dest_db.write_bytes(db_data)

            # Extract vault envelope if present
            if "vault_envelope.json" in zf.namelist():
                env_data = zf.read("vault_envelope.json")
                dest_env = (restore_root / "security" / "vault_envelope.json") if target_dir else self.key_manager.envelope.envelope_path
                dest_env.parent.mkdir(parents=True, exist_ok=True)
                dest_env.write_bytes(env_data)

            # Extract memories
            for name in zf.namelist():
                if name.startswith("memories/"):
                    rel = name[len("memories/"):]
                    target = restore_root / "memories" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))

        logger.info(f"Successfully restored vault from encrypted backup: {backup_path.name}")
        return {"status": "success", "restored_from": backup_path.name}


migration_service = MigrationService()
