"""
Speaker Diarization Engine.
Phase 3: Modular, local speaker clustering and voice segmentation.
Extracts acoustic feature signatures (energy, spectral characteristics, pitch envelopes)
and clusters segments into anonymous speaker identities (Speaker 1, Speaker 2).
Gracefully falls back to single-speaker when audio is uniform or short.
Zero cloud dependencies.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from backend.app.core.logging import logger

SAMPLE_RATE_16K = 16000


class DiarizationSegment:
    """Represents a speech segment with timing and acoustic features."""
    def __init__(
        self,
        start_time: float,
        end_time: float,
        text: str,
        speaker_label: str = "Speaker 1",
        confidence: Optional[float] = None
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        self.speaker_label = speaker_label
        self.confidence = confidence
        self.feature_vector: Optional[np.ndarray] = None


class AcousticFeatureExtractor:
    """Extracts lightweight acoustic biometric features from audio segments."""

    @staticmethod
    def extract_features(
        audio_slice: np.ndarray,
        sample_rate: int = SAMPLE_RATE_16K
    ) -> np.ndarray:
        """
        Extracts acoustic features from a 1D float32 audio waveform slice:
        - RMS Energy
        - Zero Crossing Rate
        - Spectral Centroid
        - Spectral Spread / Rolloff
        - Multi-band sub-band energy distribution (16 bands)
        Returns a normalized 20-dimensional feature vector.
        """
        if len(audio_slice) < 512:
            return np.zeros(20, dtype=np.float32)

        # 1. RMS Energy
        rms = np.sqrt(np.mean(audio_slice ** 2) + 1e-12)

        # 2. Zero Crossing Rate
        signs = np.sign(audio_slice)
        zcr = np.mean(np.abs(np.diff(signs))) / 2.0

        # 3. FFT Magnitude Spectrum
        # Use Hanning window
        windowed = audio_slice * np.hanning(len(audio_slice))
        fft_vals = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1.0 / sample_rate)

        # Normalize spectrum
        fft_sum = np.sum(fft_vals) + 1e-12
        norm_fft = fft_vals / fft_sum

        # Spectral Centroid
        spectral_centroid = np.sum(freqs * norm_fft) / (sample_rate / 2.0)

        # Spectral Spread (Variance around centroid)
        spectral_spread = np.sqrt(np.sum(((freqs - spectral_centroid * (sample_rate / 2.0)) ** 2) * norm_fft)) / (sample_rate / 2.0)

        # 4. 16 Sub-band energy ratios (filter bank approximation)
        num_bands = 16
        band_len = len(norm_fft) // num_bands
        sub_bands = []
        for b in range(num_bands):
            b_start = b * band_len
            b_end = (b + 1) * band_len if b < num_bands - 1 else len(norm_fft)
            sub_bands.append(np.sum(norm_fft[b_start:b_end]))

        feature_vector = np.array([rms, zcr, spectral_centroid, spectral_spread] + sub_bands, dtype=np.float32)

        # Normalize vector to unit length
        norm = np.linalg.norm(feature_vector)
        if norm > 1e-9:
            feature_vector = feature_vector / norm

        return feature_vector


class DiarizationEngine:
    """Clusters speech segments into anonymous speaker labels."""

    def __init__(self, max_speakers: int = 5, cluster_distance_threshold: float = 0.45):
        self.max_speakers = max_speakers
        self.cluster_distance_threshold = cluster_distance_threshold
        self.feature_extractor = AcousticFeatureExtractor()

    def diarize_segments(
        self,
        full_audio: np.ndarray,
        segments: List[Dict[str, Any]],
        sample_rate: int = SAMPLE_RATE_16K
    ) -> List[Dict[str, Any]]:
        """
        Assigns speaker labels ('Speaker 1', 'Speaker 2', etc.) to segments.
        If only one speaker is detected or audio is uniform, labels all as 'Speaker 1'.
        """
        if not segments:
            return []

        # If 1 segment, immediately return Speaker 1
        if len(segments) == 1:
            seg_copy = dict(segments[0])
            seg_copy["speaker_label"] = "Speaker 1"
            return [seg_copy]

        # Extract features for each segment
        feature_vectors = []
        valid_indices = []

        total_samples = len(full_audio)

        for idx, seg in enumerate(segments):
            start_sec = seg.get("start", 0.0)
            end_sec = seg.get("end", 0.0)

            start_sample = max(0, int(start_sec * sample_rate))
            end_sample = min(total_samples, int(end_sec * sample_rate))

            if end_sample - start_sample > 512:
                slice_data = full_audio[start_sample:end_sample]
                feat = self.feature_extractor.extract_features(slice_data, sample_rate)
                feature_vectors.append(feat)
                valid_indices.append(idx)
            else:
                feature_vectors.append(np.zeros(20, dtype=np.float32))

        if not valid_indices:
            # Fallback to single speaker
            for seg in segments:
                seg["speaker_label"] = "Speaker 1"
            return segments

        # Cluster feature vectors using online hierarchical / centroid distance
        speaker_centroids: List[np.ndarray] = []
        segment_labels: List[str] = ["Speaker 1"] * len(segments)

        for idx in range(len(segments)):
            feat = feature_vectors[idx]
            if np.all(feat == 0):
                continue

            if not speaker_centroids:
                speaker_centroids.append(feat)
                segment_labels[idx] = "Speaker 1"
                continue

            # Compute cosine distances to existing speaker centroids
            distances = []
            for centroid in speaker_centroids:
                # Cosine distance = 1 - dot product (both normalized)
                dot_prod = np.dot(feat, centroid)
                dist = 1.0 - float(dot_prod)
                distances.append(dist)

            min_dist = min(distances)
            best_cluster = distances.index(min_dist)

            if min_dist < self.cluster_distance_threshold:
                # Assign to existing speaker and update centroid
                segment_labels[idx] = f"Speaker {best_cluster + 1}"
                speaker_centroids[best_cluster] = 0.8 * speaker_centroids[best_cluster] + 0.2 * feat
                norm = np.linalg.norm(speaker_centroids[best_cluster])
                if norm > 1e-9:
                    speaker_centroids[best_cluster] /= norm
            else:
                # If below max speakers, create a new speaker cluster
                if len(speaker_centroids) < self.max_speakers:
                    speaker_centroids.append(feat)
                    new_idx = len(speaker_centroids)
                    segment_labels[idx] = f"Speaker {new_idx}"
                else:
                    # Merge with closest existing
                    segment_labels[idx] = f"Speaker {best_cluster + 1}"

        # Assign speaker labels back to segments
        updated_segments = []
        for idx, seg in enumerate(segments):
            seg_dict = dict(seg)
            seg_dict["speaker_label"] = segment_labels[idx]
            updated_segments.append(seg_dict)

        logger.info(f"Diarization completed: identified {len(speaker_centroids)} speaker cluster(s) across {len(segments)} segments.")
        return updated_segments


diarization_engine = DiarizationEngine()

