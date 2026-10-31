"""
Model Manager for Local Semantic Embeddings.
Enforces offline-first operation, whitelisted models, corruption checks,
and zero implicit/silent background downloads.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import os
import shutil
import tempfile

from backend.app.core.config import settings
from backend.app.core.logging import logger


class EmbeddingModelError(Exception):
    """Base error for embedding model issues."""
    pass


class ModelNotInstalledError(EmbeddingModelError):
    """Raised when an embedding model is requested but weights are not downloaded."""
    pass


class ModelCorruptError(EmbeddingModelError):
    """Raised when local model files are truncated, empty, hash-mismatched, or unreadable."""
    pass


def compute_file_sha256(file_path: Path) -> str:
    """Calculates SHA-256 cryptographic digest of a local file in 64KB chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class EmbeddingModelManager:
    """
    Manages local embedding model files on disk under `models/embeddings/`.
    Enforces pinned upstream revisions, cryptographic manifests, atomic staging,
    and rollback on download/hash verification failures.
    """
    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
        "multilingual-e5-small": {
            "name": "multilingual-e5-small",
            "repo_id": "intfloat/multilingual-e5-small",
            # Pinned immutable git commit revision from upstream Hugging Face
            "revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
            "dimension": 384,
            "max_sequence_length": 512,
            "description": "Multilingual E5 small (English, Hindi, and 100+ languages), lightweight 384-D embeddings for CPU.",
            "expected_files": ["tokenizer.json", "model.onnx"],
            "approx_size_mb": 135,
            # Explicit cryptographic manifest obtained from pinned upstream repository
            "manifest": {
                "model.onnx": {
                    "upstream_path": "onnx/model.onnx",
                    "sha256": "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665",
                    "size_bytes": 470268510,
                    "required": True,
                },
                "tokenizer.json": {
                    "upstream_path": "tokenizer.json",
                    "sha256": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
                    "size_bytes": 17082730,
                    "required": True,
                },
                "config.json": {
                    "upstream_path": "config.json",
                    "sha256": "69137736cab8b8903a07fe8afaafdda25aac55415a12a55d1bffa9f581abf959",
                    "size_bytes": 655,
                    "required": True,
                },
                "tokenizer_config.json": {
                    "upstream_path": "tokenizer_config.json",
                    "sha256": "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
                    "size_bytes": 443,
                    "required": False,
                },
                "special_tokens_map.json": {
                    "upstream_path": "special_tokens_map.json",
                    "sha256": "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
                    "size_bytes": 167,
                    "required": False,
                },
                "sentencepiece.bpe.model": {
                    "upstream_path": "sentencepiece.bpe.model",
                    "sha256": "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
                    "size_bytes": 5069051,
                    "required": False,
                },
            }
        }
    }

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or settings.EMBEDDING_MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str) -> Path:
        """Returns verified safe local model directory path."""
        clean_name = model_name.strip().lower()
        if clean_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported embedding model '{model_name}'. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )
        target_path = (self.models_dir / clean_name).resolve()
        # Path traversal guard
        if not str(target_path).startswith(str(self.models_dir.resolve())):
            raise ValueError("Path traversal attempt detected in model name.")
        return target_path

    def verify_manifest(self, directory: Path, model_name: str, check_hashes: bool = True) -> None:
        """
        Validates a directory against the model's pinned cryptographic manifest.
        Verifies presence of required files, exact file sizes, and cryptographic SHA-256 hashes.
        Raises ModelCorruptError if any required file is missing, truncated, or hash-mismatched.
        """
        clean_name = model_name.strip().lower()
        if clean_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unknown model '{model_name}'.")

        meta = self.SUPPORTED_MODELS[clean_name]
        manifest = meta.get("manifest", {})

        for filename, spec in manifest.items():
            file_path = directory / filename
            is_required = spec.get("required", True)
            expected_size = spec.get("size_bytes")
            expected_sha256 = spec.get("sha256")

            if not file_path.exists():
                if is_required:
                    raise ModelCorruptError(
                        f"Required model file '{filename}' missing from installation directory '{directory}'."
                    )
                continue

            # Check file size if pinned
            actual_size = file_path.stat().st_size
            if expected_size is not None and actual_size != expected_size:
                raise ModelCorruptError(
                    f"Model file '{filename}' size mismatch: expected {expected_size} bytes, "
                    f"got {actual_size} bytes (file may be truncated or corrupted)."
                )

            # Check cryptographic SHA-256 hash
            if check_hashes and expected_sha256:
                actual_sha256 = compute_file_sha256(file_path)
                if actual_sha256.lower() != expected_sha256.lower():
                    raise ModelCorruptError(
                        f"Cryptographic SHA-256 hash mismatch for '{filename}': "
                        f"expected {expected_sha256}, got {actual_sha256}."
                    )

    def is_model_installed(self, model_name: str) -> bool:
        """
        Returns True only if the model directory exists and contains valid, non-empty weights (> 1 MB).
        """
        try:
            model_dir = self.get_model_path(model_name)
            if not model_dir.exists() or not model_dir.is_dir():
                return False

            # Check required files
            onnx_file = model_dir / "model.onnx"
            tokenizer_file = model_dir / "tokenizer.json"

            if not onnx_file.exists() or onnx_file.stat().st_size <= 1024 * 1024:
                return False
            if not tokenizer_file.exists() or tokenizer_file.stat().st_size == 0:
                return False

            return True
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """Lists supported embedding models with installation status."""
        result = []
        for name, meta in self.SUPPORTED_MODELS.items():
            installed = self.is_model_installed(name)
            model_dir = self.get_model_path(name)
            size_bytes = 0
            if installed and model_dir.exists():
                for root, _, files in os.walk(model_dir):
                    for f in files:
                        p = Path(root) / f
                        if p.exists():
                            size_bytes += p.stat().st_size

            result.append({
                "name": name,
                "repo_id": meta["repo_id"],
                "revision": meta.get("revision"),
                "dimension": meta.get("dimension", 384),
                "max_sequence_length": meta.get("max_sequence_length", 512),
                "description": meta.get("description", ""),
                "installed": installed,
                "available": installed,
                "path": str(model_dir) if installed else None,
                "size_mb": round(size_bytes / (1024 * 1024), 2) if installed else 0,
                "is_default": (name == settings.EMBEDDING_DEFAULT_MODEL)
            })
        return result

    def ensure_model_available(self, model_name: str) -> Path:
        """
        Ensures model weights exist locally.
        If AUTO_DOWNLOAD_MODELS is False and weights are missing, raises ModelNotInstalledError.
        """
        clean_name = model_name.strip().lower()
        model_dir = self.get_model_path(clean_name)

        if not self.is_model_installed(clean_name):
            if not getattr(settings, "AUTO_DOWNLOAD_MODELS", False):
                raise ModelNotInstalledError(
                    f"Embedding model '{clean_name}' is not installed locally at '{model_dir}'. "
                    "Automatic background downloading is disabled to protect privacy and bandwidth. "
                    "Please install the model explicitly using the UI or API."
                )
            logger.info(f"Auto-download triggered for embedding model '{clean_name}'...")
            self.download_model(clean_name)

        return model_dir

    def download_model(self, model_name: str) -> Path:
        """
        Explicit user-initiated model download.
        Streams weights and tokenizer into an isolated temporary directory first,
        verifies file integrity against pinned upstream SHA-256 hashes, and atomically installs to `models/embeddings/{model_name}`.
        Preserves any existing working installation if verification fails.
        """
        clean_name = model_name.strip().lower()
        if clean_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unknown model name '{model_name}'.")

        meta = self.SUPPORTED_MODELS[clean_name]
        dest_dir = self.get_model_path(clean_name)
        staging_dir = Path(tempfile.mkdtemp(prefix=f"dl_{clean_name}_"))
        revision = meta.get("revision")

        logger.info(
            f"Downloading embedding model '{meta['repo_id']}' (pinned revision: {revision}) "
            f"to staging directory {staging_dir}..."
        )
        try:
            from huggingface_hub import hf_hub_download
            repo_id = meta["repo_id"]

            manifest = meta.get("manifest", {})
            for filename, spec in manifest.items():
                upstream_file = spec.get("upstream_path", filename)
                try:
                    hf_hub_download(
                        repo_id=repo_id,
                        filename=upstream_file,
                        revision=revision,
                        local_dir=str(staging_dir),
                        local_dir_use_symlinks=False
                    )
                except Exception as ex:
                    if spec.get("required", True):
                        raise ModelCorruptError(
                            f"Failed to download required model file '{upstream_file}': {ex}"
                        )
                    logger.warning(f"Optional file '{upstream_file}' could not be downloaded: {ex}")

            # Flatten nested onnx directory if present
            nested_onnx = staging_dir / "onnx" / "model.onnx"
            if nested_onnx.exists():
                shutil.move(str(nested_onnx), str(staging_dir / "model.onnx"))

            # Clean empty onnx folder in staging if present
            if (staging_dir / "onnx").exists():
                shutil.rmtree(str(staging_dir / "onnx"), ignore_errors=True)

            # Strictly verify manifest in staging BEFORE touching destination
            self.verify_manifest(staging_dir, clean_name, check_hashes=True)

            # Atomic swap to preserve existing model if swap fails
            backup_dir = None
            if dest_dir.exists():
                backup_dir = dest_dir.parent / f"{dest_dir.name}_backup_{os.getpid()}"
                shutil.move(str(dest_dir), str(backup_dir))

            try:
                dest_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staging_dir), str(dest_dir))
                if backup_dir and backup_dir.exists():
                    shutil.rmtree(str(backup_dir), ignore_errors=True)
            except Exception as swap_err:
                logger.error(f"Atomic swap failed; rolling back to existing installation: {swap_err}")
                if backup_dir and backup_dir.exists():
                    shutil.move(str(backup_dir), str(dest_dir))
                raise swap_err

            if not self.is_model_installed(clean_name):
                raise ModelCorruptError(f"Installed weights for '{clean_name}' appear invalid or incomplete.")

            logger.info(f"Embedding model '{clean_name}' successfully verified and installed at {dest_dir}.")
            return dest_dir

        except Exception as e:
            logger.error(f"Failed to download embedding model '{clean_name}': {e}")
            raise
        finally:
            if staging_dir.exists():
                shutil.rmtree(str(staging_dir), ignore_errors=True)


embedding_model_manager = EmbeddingModelManager()

