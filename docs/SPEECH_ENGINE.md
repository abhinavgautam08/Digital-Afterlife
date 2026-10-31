# Speech Engine Architecture & Operational Guide

**Digital Afterlife – Memory Keeper**  
**Subsystem**: Speech-to-Text & Diarization  
**Engine**: `faster-whisper` (CTranslate2 backend)  
**Status**: `IMPLEMENTED, MOCK-TESTED ONLY` (Real inference `BLOCKED` until user explicitly downloads model weights)

---

## 1. Architectural Overview

The speech subsystem is engineered to operate on standard consumer hardware without requiring discrete GPUs or cloud APIs.

```
[Audio/Video Input] (MP3, WAV, M4A, OGG, FLAC)
        │
        ▼
[AudioConverter] ──> PyAV / Wave decoding ──> 16 kHz Mono Float32
        │
        ▼
[TranscriptionWorker] (Concurrency = 1, Persistent SQLite Queue)
        │
        ├─► [TranscriptionEngine] ──> faster-whisper (CPU int8)
        │                                  │
        │                                  ▼
        │                         Timestamped Segments & Text
        │                                  │
        ├─► [DiarizationEngine] (Experimental Acoustic Grouping)
        │         │
        │         ▼
        │    Acoustic Features (20-D) & Anonymous Clustering
        │         │
        │         ▼
        │    "Speaker 1", "Speaker 2" Labels (Anonymous by Default)
        │
        ▼
[Database Persistence] ──> Transcript & TranscriptSegment rows (speaker_id = NULL)
```

---

## 2. Resource & Quantization Profile

- **Device**: Strictly `cpu`.
- **Quantization**: `int8` (CTranslate2 weight quantization).
- **Concurrency**: `1`. Transcription jobs execute sequentially via a background daemon thread.
- **RAM Headroom Management**:
  - The engine keeps at most **one model in RAM** at a time.
  - Calling `unload_model()` explicitly evicts the active model and triggers Python garbage collection (`gc.collect()`).
  - Switching from `base` to `tiny` evicts `base` before loading `tiny`.
- **Memory Footprint**:
  - `tiny` (~75 MB disk, ~250 MB RAM during inference).
  - `base` (~145 MB disk, ~450 MB RAM during inference).
  - `small` (~480 MB disk, ~1.1 GB RAM during inference).
- Target system headroom: 12 GB RAM with desktop browser and background processes running concurrently.

---

## 3. Audio Ingestion & Formats

The engine accepts all 5 supported audio formats:
- `.mp3`
- `.wav`
- `.m4a`
- `.ogg`
- `.flac`
- Video containers with audio tracks (`.mp4`, `.webm`, `.mov`).

### Decoding Strategy
1. **PyAV (`av`)**: Uses direct C-binding FFmpeg libraries compiled into Python wheels. Requires no system FFmpeg binary installation on Windows.
2. **Standard Library `wave`**: Fallback for uncompressed PCM WAV files.
3. **Resampling**: All incoming streams are resampled to 16,000 Hz, single channel (mono), and normalized to `[-1.0, 1.0]` float32.

---

## 4. Speaker Diarization: Classification & Limitations

### Classification
- **Type**: `EXPERIMENTAL HEURISTIC ACOUSTIC GROUPING`.
- **Not Implemented**: Heavy neural speaker embedding (e.g. ECAPA-TDNN, x-vectors, pyannote.audio) is deliberately NOT implemented to preserve the 12 GB RAM / pure CPU boundary.

### How It Works
1. **Segment Slicing**: Uses boundaries detected by `faster-whisper`'s internal VAD (`vad_filter=True`, `min_silence_duration_ms=500`).
2. **Acoustic Feature Extraction**: Extracts 20 normalized dimensions:
   - Root Mean Square (RMS) energy.
   - Zero-crossing rate.
   - Spectral centroid (frequency balance).
   - Spectral spread / rolloff.
   - 16-band sub-band spectral distribution.
3. **Cosine Clustering**: Computes pairwise cosine distance against cluster centroids.
4. **Anonymous Tagging**: Labels segments as `Speaker 1`, `Speaker 2`, etc.
5. **Fallback**: If audio is uniform or variance is below distance threshold (0.45), labels all speech as `Speaker 1`.

### Known Limitations
- Background noise, varying microphone distances, and pitch changes can cause inaccurate cluster assignments.
- Clusters across wide recording intervals or different audio files may drift.
- All speaker labels must be treated as experimental suggestions until manually confirmed by the user.

---

## 5. Offline Model Management & Safeguards

- **Directory**: `models/whisper/{model_name}/`.
- **Zero Silent Downloads**: If a user attempts to transcribe with an uninstalled model while `AUTO_DOWNLOAD_MODELS=False`, the API returns HTTP 400 Bad Request instructing the user to download the model explicitly.
- **Corrupt File Detection**: Verifies that `model.bin` is > 1 MB and `config.json` exists. Corrupt or truncated files trigger `ModelCorruptError`.
- **Explicit Trigger**: Downloads only initiate via `POST /api/transcription/models/download` or the Settings UI button.
