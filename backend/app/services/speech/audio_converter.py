"""
Audio Preprocessing and Format Conversion.
Converts any supported audio format (MP3, WAV, M4A, OGG, FLAC) to 16 kHz mono PCM WAV.
Uses PyAV (av) for robust in-process decoding with fallbacks to standard wave.
Supports chunking for long recordings with overlapping boundaries.
"""
import io
import math
import wave
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Union
import numpy as np
from backend.app.core.logging import logger

SAMPLE_RATE_16K = 16000


class AudioConverter:
    """Handles audio loading, resampling to 16 kHz mono, and chunking."""

    @staticmethod
    def is_ffmpeg_cli_available() -> bool:
        """Checks if ffmpeg binary exists in PATH."""
        import shutil
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def load_audio_as_float32(
        file_path_or_bytes: Union[str, Path, bytes],
        target_sample_rate: int = SAMPLE_RATE_16K
    ) -> Tuple[np.ndarray, float]:
        """
        Loads an audio file and resamples/converts it to a 1D float32 numpy array
        normalized between -1.0 and 1.0 at 16,000 Hz mono.
        Returns:
            (samples_np_array, duration_seconds)
        """
        try:
            import av

            if isinstance(file_path_or_bytes, bytes):
                container = av.open(io.BytesIO(file_path_or_bytes))
            else:
                container = av.open(str(file_path_or_bytes))

            # Select first audio stream
            audio_stream = next((s for s in container.streams if s.type == "audio"), None)
            if not audio_stream:
                raise ValueError("No audio stream found in media container.")

            # Set up resampler to target sample rate, mono, s16 or flt format
            resampler = av.AudioResampler(
                format="flt",
                layout="mono",
                rate=target_sample_rate
            )

            all_frames: List[np.ndarray] = []
            for frame in container.decode(audio_stream):
                resampled = resampler.resample(frame)
                for resampled_frame in resampled:
                    # Convert to numpy array
                    arr = resampled_frame.to_ndarray()
                    if arr.ndim > 1:
                        arr = arr[0]  # Mono channel
                    all_frames.append(arr)

            # Flush resampler
            for resampled_frame in resampler.resample(None):
                arr = resampled_frame.to_ndarray()
                if arr.ndim > 1:
                    arr = arr[0]
                all_frames.append(arr)

            container.close()

            if not all_frames:
                raise ValueError("Decoded audio contains no audio frames.")

            audio_data = np.concatenate(all_frames).astype(np.float32)
            duration = float(len(audio_data)) / float(target_sample_rate)
            return audio_data, duration

        except Exception as e:
            logger.warning(f"PyAV audio decoding encountered {e}. Attempting WAV fallback...")
            return AudioConverter._wave_fallback(file_path_or_bytes, target_sample_rate)

    @staticmethod
    def _wave_fallback(
        file_path_or_bytes: Union[str, Path, bytes],
        target_sample_rate: int = SAMPLE_RATE_16K
    ) -> Tuple[np.ndarray, float]:
        """Fallback for standard PCM WAV files using standard library wave module."""
        if isinstance(file_path_or_bytes, bytes):
            wav_file = wave.open(io.BytesIO(file_path_or_bytes), "rb")
        else:
            wav_file = wave.open(str(file_path_or_bytes), "rb")

        with wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            num_frames = wav_file.getnframes()
            raw_bytes = wav_file.readframes(num_frames)

        # Convert raw bytes according to sample width
        if sample_width == 1:
            dtype = np.uint8
            data = (np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            dtype = np.int16
            data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32) / 32768.0
        elif sample_width == 4:
            dtype = np.int32
            data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        # Mix down multi-channel to mono
        if channels > 1:
            data = data.reshape(-1, channels)
            data = np.mean(data, axis=1)

        # Resample to 16 kHz if necessary
        if framerate != target_sample_rate:
            num_target_samples = int(len(data) * target_sample_rate / framerate)
            indices = np.linspace(0, len(data) - 1, num_target_samples)
            data = np.interp(indices, np.arange(len(data)), data).astype(np.float32)

        duration = float(len(data)) / float(target_sample_rate)
        return data, duration

    @staticmethod
    def convert_to_wav_bytes(
        audio_data: np.ndarray,
        sample_rate: int = SAMPLE_RATE_16K
    ) -> bytes:
        """Converts float32 audio numpy array back into 16-bit PCM WAV bytes."""
        # Clip to -1.0 .. 1.0 and convert to int16
        clipped = np.clip(audio_data, -1.0, 1.0)
        pcm_16 = (clipped * 32767.0).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_16.tobytes())

        return buffer.getvalue()

    @staticmethod
    def save_to_16k_mono_wav(
        source_path: Union[str, Path],
        target_path: Union[str, Path]
    ) -> float:
        """
        Converts any source audio file into a 16 kHz mono WAV file at target_path.
        Returns duration in seconds.
        """
        audio_data, duration = AudioConverter.load_audio_as_float32(source_path)
        wav_bytes = AudioConverter.convert_to_wav_bytes(audio_data, SAMPLE_RATE_16K)
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(wav_bytes)
        return duration

    @staticmethod
    def chunk_audio(
        audio_data: np.ndarray,
        sample_rate: int = SAMPLE_RATE_16K,
        chunk_duration_sec: float = 30.0,
        overlap_sec: float = 1.0
    ) -> Generator[Tuple[int, float, float, np.ndarray], None, None]:
        """
        Slices audio into chunks with overlap for bounded memory processing.
        Yields: (chunk_index, start_sec, end_sec, chunk_array)
        """
        total_samples = len(audio_data)
        chunk_samples = int(chunk_duration_sec * sample_rate)
        overlap_samples = int(overlap_sec * sample_rate)
        step_samples = chunk_samples - overlap_samples

        if total_samples <= chunk_samples:
            yield 0, 0.0, float(total_samples) / sample_rate, audio_data
            return

        idx = 0
        current_sample = 0
        while current_sample < total_samples:
            end_sample = min(current_sample + chunk_samples, total_samples)
            chunk = audio_data[current_sample:end_sample]
            start_sec = float(current_sample) / sample_rate
            end_sec = float(end_sample) / sample_rate

            yield idx, start_sec, end_sec, chunk

            if end_sample >= total_samples:
                break

            current_sample += step_samples
            idx += 1


audio_converter = AudioConverter()

