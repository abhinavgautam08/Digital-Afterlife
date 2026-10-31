"""
Whisper Model Manager.
Handles offline-first model discovery, verification, and explicit user-initiated downloads.
Strictly prevents automatic or silent model downloading over the internet.
"""
import os
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Supported models with their typical disk sizes and descriptions
SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
    "tiny": {
        "name": "tiny",
        "description": "Fastest and smallest model (~75 MB). Good for quick previews and clear speech.",
        "disk_size_mb": 75,
        "repo_id": "Systran/faster-whisper-tiny",
        "recommended": False,
    },
    "base": {
        "name": "base",
        "description": "Standard balanced model (~145 MB). Recommended for everyday CPU transcription.",
        "disk_size_mb": 145,
        "repo_id": "Systran/faster-whisper-base",
        "recommended": True,
    },
    "small": {
        "name": "small",
        "description": "High accuracy model (~480 MB). Better multilingual recognition (English & Hindi).",
        "disk_size_mb": 480,
        "repo_id": "Systran/faster-whisper-small",
        "recommended": False,
    },
}

_download_lock = threading.Lock()
_active_downloads: Dict[str, float] = {}


class ModelManager:
    """Manages local Whisper model storage and explicit downloads."""

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or settings.WHISPER_MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_directory(self, model_name: str) -> Path:
        """Returns the directory path where a specific model is stored."""
        return self.models_dir / model_name.lower()

    def is_model_installed(self, model_name: str) -> bool:
        """
        Checks whether the specified model is present locally and has essential files
        (model.bin, vocabulary, config, etc.).
        """
        model_name = model_name.lower()
        model_path = self.get_model_directory(model_name)
        if not model_path.is_dir():
            return False

        # ctranslate2 / faster-whisper required files
        model_bin = model_path / "model.bin"
        config_json = model_path / "config.json"
        tokenizer = model_path / "tokenizer.json"

        # Model is installed if model.bin exists, is non-empty (>1MB), and metadata exists
        try:
            if not model_bin.is_file() or model_bin.stat().st_size < 1024 * 1024:
                return False
        except OSError:
            return False

        return config_json.is_file() or tokenizer.is_file()

    def get_model_size_on_disk(self, model_name: str) -> int:
        """Returns total bytes used by the installed model on disk."""
        model_path = self.get_model_directory(model_name)
        if not model_path.is_dir():
            return 0
        total_size = 0
        for dirpath, _, filenames in os.walk(model_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
        return total_size

    def list_models(self) -> List[Dict[str, Any]]:
        """Lists all supported models with their local installation status."""
        results = []
        for name, meta in SUPPORTED_MODELS.items():
            installed = self.is_model_installed(name)
            disk_bytes = self.get_model_size_on_disk(name) if installed else 0
            is_downloading = name in _active_downloads
            progress = _active_downloads.get(name, 0.0)

            results.append({
                "name": name,
                "description": meta["description"],
                "disk_size_mb": meta["disk_size_mb"],
                "actual_size_mb": round(disk_bytes / (1024 * 1024), 2) if installed else 0.0,
                "is_installed": installed,
                "is_downloading": is_downloading,
                "download_progress": progress,
                "recommended": meta["recommended"],
                "local_path": str(self.get_model_directory(name)) if installed else None,
            })
        return results

    def download_model(self, model_name: str, force: bool = False) -> Path:
        """
        Explicitly downloads a Whisper model to the local directory.
        MUST only be triggered by an explicit user request.
        """
        model_name = model_name.lower()
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}. Supported: {list(SUPPORTED_MODELS.keys())}")

        target_dir = self.get_model_directory(model_name)

        if self.is_model_installed(model_name) and not force:
            logger.info(f"Model '{model_name}' is already installed at {target_dir}")
            return target_dir

        with _download_lock:
            if model_name in _active_downloads:
                raise RuntimeError(f"Download for model '{model_name}' is already in progress.")
            _active_downloads[model_name] = 0.0

        try:
            logger.info(f"Starting explicit download of Whisper model '{model_name}' to {target_dir}...")
            repo_id = SUPPORTED_MODELS[model_name]["repo_id"]

            from faster_whisper import download_model as fw_download_model

            _active_downloads[model_name] = 10.0
            # Download model files into the specific target directory
            downloaded_dir = fw_download_model(
                size_or_id=repo_id,
                output_dir=str(target_dir),
                local_files_only=False,
            )
            _active_downloads[model_name] = 100.0
            logger.info(f"Successfully downloaded Whisper model '{model_name}' to {downloaded_dir}")
            return Path(downloaded_dir)
        except Exception as e:
            logger.error(f"Failed to download Whisper model '{model_name}': {e}")
            # Clean up partial directory if download failed
            if target_dir.exists() and not self.is_model_installed(model_name):
                try:
                    shutil.rmtree(target_dir)
                except Exception:
                    pass
            raise RuntimeError(f"Model download failed: {str(e)}") from e
        finally:
            with _download_lock:
                _active_downloads.pop(model_name, None)

    def delete_model(self, model_name: str) -> bool:
        """Deletes a locally downloaded model to reclaim disk space."""
        model_name = model_name.lower()
        target_dir = self.get_model_directory(model_name)
        if not target_dir.exists():
            return False
        shutil.rmtree(target_dir)
        logger.info(f"Deleted local model directory for '{model_name}'")
        return True


model_manager = ModelManager()

