"""
Local Speech-to-Text Transcription Engine using faster-whisper.
Runs on CPU with int8 quantization.
Loads exclusively from local model storage without silent network requests.
Supports English, Hindi, and multilingual speech transcription.
"""
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.speech.model_manager import model_manager
from backend.app.services.speech.audio_converter import audio_converter, SAMPLE_RATE_16K


class ModelNotInstalledError(Exception):
    """Raised when attempting to transcribe with a model that is not installed locally."""
    pass


class ModelCorruptError(Exception):
    """Raised when local model files exist but are unreadable, truncated, or corrupt."""
    pass


class TranscriptionEngine:
    """Wrapper around faster-whisper WhisperModel for local CPU inference."""

    def __init__(self):
        self._current_model_name: Optional[str] = None
        self._current_model: Optional[Any] = None

    def unload_model(self) -> None:
        """Unloads the active Whisper model from RAM to reclaim memory."""
        if self._current_model is not None:
            logger.info(f"Unloading Whisper model '{self._current_model_name}' from RAM...")
            del self._current_model
            self._current_model = None
            self._current_model_name = None
            import gc
            gc.collect()

    def get_model(self, model_name: str = "base"):
        """
        Loads and returns the active WhisperModel instance on CPU with int8 quantization.
        Evicts any previously loaded model to ensure only ONE model resides in RAM at a time.
        """
        model_name = model_name.lower()

        if self._current_model_name == model_name and self._current_model is not None:
            return self._current_model

        # Evict prior model to prevent accumulating multiple models in memory
        if self._current_model is not None:
            self.unload_model()

        # Verify offline availability
        if not model_manager.is_model_installed(model_name):
            if settings.AUTO_DOWNLOAD_MODELS:
                logger.info(f"Auto-download enabled. Downloading '{model_name}'...")
                model_manager.download_model(model_name)
            else:
                raise ModelNotInstalledError(
                    f"Whisper model '{model_name}' is not installed locally. "
                    f"Please download it explicitly via the Settings page or /api/transcription/models/download."
                )

        model_dir = str(model_manager.get_model_directory(model_name))
        logger.info(f"Loading faster-whisper model '{model_name}' from {model_dir} on CPU (int8)...")

        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(
                model_size_or_path=model_dir,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                cpu_threads=settings.WHISPER_CPU_THREADS,
                local_files_only=True,
            )
        except Exception as e:
            logger.error(f"Failed to load Whisper model files from {model_dir}: {e}")
            raise ModelCorruptError(
                f"Model files for '{model_name}' at {model_dir} appear to be missing or corrupt: {e}"
            ) from e

        self._current_model = model
        self._current_model_name = model_name
        return model

    def transcribe(
        self,
        audio_source: Union[str, Path, np.ndarray],
        model_name: str = "base",
        language: str = "auto",
        initial_prompt: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Transcribes the given audio source into text and timestamped segments.

        Returns a dictionary containing:
        - full_text: complete transcript string
        - detected_language: ISO language code (e.g. 'en', 'hi')
        - language_probability: confidence of language detection
        - segments: list of dicts with start, end, text, confidence
        - processing_duration: seconds elapsed during inference
        - audio_duration: total audio duration in seconds
        """
        start_clock = time.perf_counter()

        # Preprocess audio into 16 kHz float32 array if needed
        if isinstance(audio_source, (str, Path)):
            audio_data, audio_duration = audio_converter.load_audio_as_float32(audio_source)
        elif isinstance(audio_source, np.ndarray):
            audio_data = audio_source.astype(np.float32)
            audio_duration = float(len(audio_data)) / SAMPLE_RATE_16K
        else:
            raise ValueError(f"Unsupported audio source type: {type(audio_source)}")

        whisper_model = self.get_model(model_name)

        whisper_lang = None if language.lower() in ("auto", "", "detect") else language.lower()

        logger.info(
            f"Transcribing audio ({audio_duration:.2f}s) using model '{model_name}' "
            f"with language='{whisper_lang or 'auto'}'..."
        )

        segments_generator, info = whisper_model.transcribe(
            audio_data,
            language=whisper_lang,
            initial_prompt=initial_prompt,
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        detected_lang = info.language
        lang_prob = info.language_probability

        collected_segments: List[Dict[str, Any]] = []
        text_parts: List[str] = []

        for seg in segments_generator:
            # Convert avg_logprob to confidence between 0.0 and 1.0
            confidence = None
            if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
                confidence = round(min(1.0, max(0.0, math.exp(seg.avg_logprob))), 4)

            segment_dict = {
                "start": round(float(seg.start), 2),
                "end": round(float(seg.end), 2),
                "text": seg.text.strip(),
                "confidence": confidence,
            }
            collected_segments.append(segment_dict)
            text_parts.append(seg.text.strip())

            if progress_callback and audio_duration > 0:
                current_progress = min(0.95, float(seg.end) / audio_duration)
                progress_callback(current_progress)

        full_text = " ".join(text_parts).strip()
        processing_time = round(time.perf_counter() - start_clock, 2)

        logger.info(
            f"Transcription complete in {processing_time}s: {len(collected_segments)} segments, "
            f"detected_language='{detected_lang}' (p={lang_prob:.2f})."
        )

        return {
            "full_text": full_text,
            "detected_language": detected_lang,
            "language_probability": round(float(lang_prob), 4),
            "segments": collected_segments,
            "audio_duration": round(audio_duration, 2),
            "processing_duration": processing_time,
            "audio_data": audio_data,
        }


transcription_engine = TranscriptionEngine()

