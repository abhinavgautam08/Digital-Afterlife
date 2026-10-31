"""
Audio processing module for Phase 2.
Extracts audio duration, sample rate, bitrate, channels, and generates waveform peak arrays
for visual playback in the Memory Vault.
"""
from typing import Dict, Any, List, Optional
import io
import math
import wave
import struct

from backend.app.core.logging import logger

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.oggvorbis import OggVorbis
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False


def generate_simple_waveform(file_bytes: bytes, num_points: int = 60) -> List[float]:
    """
    Generates a normalized float array [0.0 - 1.0] representing audio amplitude
    for visual waveform preview in the frontend.
    """
    try:
        # Check if file is a standard WAV file
        if file_bytes.startswith(b"RIFF") and b"WAVE" in file_bytes[:12]:
            with wave.open(io.BytesIO(file_bytes), "rb") as wav:
                n_frames = wav.getnframes()
                sampwidth = wav.getsampwidth()
                if n_frames > 0 and sampwidth in (1, 2):
                    chunk_size = max(1, n_frames // num_points)
                    points = []
                    for _ in range(num_points):
                        frames = wav.readframes(chunk_size)
                        if not frames:
                            break
                        if sampwidth == 2:
                            # 16-bit signed PCM
                            fmt = f"<{len(frames)//2}h"
                            samples = struct.unpack(fmt, frames)
                            peak = max(abs(s) for s in samples) if samples else 0
                            points.append(min(1.0, round(peak / 32768.0, 3)))
                        else:
                            # 8-bit unsigned
                            peak = max(abs(b - 128) for b in frames) if frames else 0
                            points.append(min(1.0, round(peak / 128.0, 3)))

                    if points:
                        # Pad if needed
                        while len(points) < num_points:
                            points.append(0.05)
                        return points
    except Exception as e:
        logger.debug(f"Waveform raw PCM extraction fallback: {e}")

    # Deterministic fallback pattern for compressed formats (MP3/OGG/FLAC) based on byte variance
    points = []
    chunk_size = max(1, len(file_bytes) // num_points)
    for i in range(num_points):
        start = i * chunk_size
        chunk = file_bytes[start : start + chunk_size]
        if not chunk:
            points.append(0.1)
            continue
        avg = sum(chunk) / len(chunk)
        # Normalize pseudo-amplitude variance
        variance = abs(avg - 128) / 128
        points.append(round(min(1.0, max(0.08, variance * 1.5)), 3))

    return points


def process_audio(
    file_bytes: bytes,
    file_format: str
) -> Dict[str, Any]:
    """
    Extracts duration, channel info, and sample rate from audio artifacts.
    """
    duration_seconds: Optional[float] = None
    meta: Dict[str, Any] = {"format": file_format}

    if HAS_MUTAGEN:
        try:
            audio_io = io.BytesIO(file_bytes)
            audio = mutagen.File(audio_io)
            if audio is not None and audio.info is not None:
                duration_seconds = round(float(getattr(audio.info, "length", 0.0)), 2)
                meta["sample_rate"] = getattr(audio.info, "sample_rate", None)
                meta["channels"] = getattr(audio.info, "channels", None)
                meta["bitrate"] = getattr(audio.info, "bitrate", None)
        except Exception as e:
            logger.debug(f"Mutagen audio parse error: {e}")

    # Fallback to standard wave module if duration still unknown and format is wav
    if duration_seconds is None and file_format == "wav":
        try:
            with wave.open(io.BytesIO(file_bytes), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate > 0:
                    duration_seconds = round(frames / float(rate), 2)
                    meta["sample_rate"] = rate
                    meta["channels"] = wav.getnchannels()
        except Exception:
            pass

    waveform_peaks = generate_simple_waveform(file_bytes, num_points=50)
    meta["waveform"] = waveform_peaks

    return {
        "duration_seconds": duration_seconds,
        "width": None,
        "height": None,
        "thumbnail_path": None,
        "extracted_text": None,
        "original_created_at": None,
        "metadata": meta,
        "waveform": waveform_peaks
    }

