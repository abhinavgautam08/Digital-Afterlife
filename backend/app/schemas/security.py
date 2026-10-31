"""
Pydantic schemas for Phase 6: Encryption, Vault Management, and Safe Migration.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class VaultStatusResponse(BaseModel):
    is_initialized: bool
    is_unlocked: bool
    algorithm: str = "AES-256-GCM"
    kdf: str = "Argon2id"
    auto_lock_minutes: int = 15
    total_files: int = 0
    encrypted_files: int = 0
    plaintext_files: int = 0
    is_fully_encrypted: bool = False

    model_config = ConfigDict(from_attributes=True)


class VaultSetupRequest(BaseModel):
    password: str = Field(..., min_length=8, description="Vault master passphrase (minimum 8 characters)")
    auto_lock_minutes: int = Field(default=15, ge=1, le=1440)


class VaultSetupResponse(BaseModel):
    status: str = "success"
    recovery_key: str
    message: str


class VaultUnlockRequest(BaseModel):
    password: Optional[str] = None
    recovery_key: Optional[str] = None


class VaultPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class VaultRecoverRequest(BaseModel):
    recovery_key: str
    new_password: str = Field(..., min_length=8)


class MigrationStatusResponse(BaseModel):
    is_running: bool
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    progress_percent: float
    errors: List[str] = Field(default_factory=list)
    cancelled: bool = False
    completed_at: Optional[str] = None
    backup_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

