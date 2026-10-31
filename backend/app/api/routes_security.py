"""
Security, Vault Key Management, and Migration API Routes.
Phase 6: Authenticated AES-256-GCM vault lifecycle, Argon2id derivation,
safe file migration, and encrypted backups.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import FileResponse

from backend.app.core.crypto import (
    vault_key_manager,
    VaultLockedError,
    InvalidPasswordError,
    CryptoError,
)
from backend.app.schemas.security import (
    VaultStatusResponse,
    VaultSetupRequest,
    VaultSetupResponse,
    VaultUnlockRequest,
    VaultPasswordChangeRequest,
    VaultRecoverRequest,
    MigrationStatusResponse,
)
from backend.app.services.encryption.migration_service import migration_service
from backend.app.core.logging import logger

router = APIRouter(prefix="/security", tags=["Vault Security & Encryption"])


@router.get("/status", response_model=VaultStatusResponse)
@router.get("/vault/status", response_model=VaultStatusResponse)
def get_vault_status():
    """Retrieves vault initialization, lock state, algorithm metadata, and encryption coverage."""
    scan_res = migration_service.scan_files()
    return VaultStatusResponse(
        is_initialized=vault_key_manager.is_initialized(),
        is_unlocked=vault_key_manager.is_unlocked(),
        algorithm="AES-256-GCM",
        kdf="Argon2id",
        auto_lock_minutes=vault_key_manager._auto_lock_minutes,
        total_files=scan_res["total_files"],
        encrypted_files=scan_res["encrypted_count"],
        plaintext_files=scan_res["plaintext_count"],
        is_fully_encrypted=scan_res["is_fully_encrypted"],
    )


@router.post("/setup", response_model=VaultSetupResponse)
@router.post("/vault/setup", response_model=VaultSetupResponse)
def setup_vault(req: VaultSetupRequest):
    """Initializes vault with a master passphrase and returns a 32-character recovery key."""
    if vault_key_manager.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault is already initialized."
        )
    try:
        recovery_key = vault_key_manager.setup_vault(
            password=req.password,
            auto_lock_minutes=req.auto_lock_minutes
        )
        return VaultSetupResponse(
            status="success",
            recovery_key=recovery_key,
            message="Vault encryption initialized. Store your recovery key safely in an offline location."
        )
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/unlock")
@router.post("/vault/unlock")
def unlock_vault(req: VaultUnlockRequest):
    """Unlocks the memory vault using master passphrase or recovery key."""
    if not vault_key_manager.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault is not initialized. Please run setup first."
        )

    try:
        if req.password:
            vault_key_manager.unlock_with_password(req.password)
            return {"status": "unlocked", "method": "password"}
        elif req.recovery_key:
            vault_key_manager.unlock_with_recovery_key(req.recovery_key)
            return {"status": "unlocked", "method": "recovery_key"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either password or recovery_key must be provided."
            )
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/lock")
@router.post("/vault/lock")
def lock_vault():
    """Explicitly locks the vault and zeroes out sensitive cryptographic keys in memory."""
    vault_key_manager.lock()
    return {"status": "locked", "message": "Vault locked and memory keys securely zeroed."}


@router.post("/change-password")
@router.post("/vault/change-password")
def change_password(req: VaultPasswordChangeRequest):
    """Changes the vault master passphrase and re-wraps the DEK without re-encrypting media."""
    try:
        vault_key_manager.envelope.rewrap_dek_with_new_password(
            current_password=req.current_password,
            new_password=req.new_password
        )
        return {"status": "success", "message": "Master passphrase updated and DEK re-wrapped successfully."}
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/recover")
def recover_vault(req: VaultRecoverRequest):
    """Resets master passphrase using the emergency recovery key."""
    try:
        vault_key_manager.envelope.reset_password_with_recovery_key(
            recovery_key=req.recovery_key,
            new_password=req.new_password
        )
        return {"status": "success", "message": "Passphrase reset successfully using recovery key."}
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# File Encryption Migration Endpoints
# -----------------------------------------------------------------------------

@router.post("/migrate", response_model=MigrationStatusResponse)
def start_file_migration():
    """Starts user-controlled safe file encryption migration with progress tracking."""
    try:
        status_dict = migration_service.start_migration(background=True)
        return MigrationStatusResponse(**status_dict)
    except VaultLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/migrate/status", response_model=MigrationStatusResponse)
def get_migration_status():
    """Returns current progress of active file encryption migration."""
    return MigrationStatusResponse(**migration_service.status.to_dict())


@router.post("/migrate/cancel")
def cancel_file_migration():
    """Requests graceful cancellation of active migration."""
    migration_service.cancel_migration()
    return {"status": "cancelling", "message": "Migration cancellation requested."}


@router.post("/migrate/rollback")
def rollback_migration():
    """Rolls back migrated files from the pre-migration plaintext backup directory."""
    try:
        return migration_service.rollback_migration()
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Encrypted Backups
# -----------------------------------------------------------------------------

@router.post("/backup")
def create_vault_backup():
    """Creates a unified authenticated AES-256-GCM encrypted vault backup archive."""
    try:
        backup_path = migration_service.create_encrypted_backup()
        return {
            "status": "success",
            "backup_filename": backup_path.name,
            "size_bytes": backup_path.stat().st_size,
            "message": "Unified encrypted backup created successfully."
        }
    except VaultLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/restore")
async def restore_vault_backup(file: UploadFile = File(...)):
    """Restores database and files from an authenticated encrypted backup archive (.da-backup)."""
    if not vault_key_manager.is_unlocked():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Vault must be unlocked to restore backup.")

    temp_path = Path("temp_restore_upload.da-backup")
    try:
        content = await file.read()
        temp_path.write_bytes(content)
        result = migration_service.restore_encrypted_backup(temp_path)
        return result
    except CryptoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        temp_path.unlink(missing_ok=True)
