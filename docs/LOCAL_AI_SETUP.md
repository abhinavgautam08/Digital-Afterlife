# Local AI Runtimes Setup & Operational Guide

**Application**: Digital Afterlife – Memory Keeper  
**Version**: 0.4.0  
**Guarantees**: Zero Cloud Subscriptions, Zero Telemetry, 100% Offline Operation

Digital Afterlife utilizes two local AI engines operating in tandem:
1. **Ollama**: Local open-weight Large Language Model daemon (`qwen2.5:3b-instruct`).
2. **Local CPU ONNX Runtimes**: Quantized embedding (`multilingual-e5-small`) and speech-to-text (`faster-whisper base`).

---

## 1. System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux.
- **CPU**: Modern x86_64 or ARM64 processor (4+ cores recommended).
- **RAM**: Minimum 8 GB; 12 GB+ recommended for simultaneous LLM and embedding operations.
- **GPU**: None required. All models run quantized on CPU.
- **Disk Space**: ~3.5 GB total for models and virtual environment.

---

## 2. Ollama LLM Setup (Qwen 2.5 3B)

### Step 1: Install Ollama
Download and install Ollama from [https://ollama.ai](https://ollama.ai).

### Step 2: Start the Ollama Daemon
Ensure Ollama is running and listening on `http://127.0.0.1:11434`.

### Step 3: Pull the Recommended Model
In your terminal, pull the Apache 2.0 open-weight model:
```bash
ollama pull qwen2.5:3b
```

### Step 4: Verify Ollama Status
In the Digital Afterlife UI, the top badge will turn green and read **"Ollama Online"**. You can also test in your browser at `http://127.0.0.1:11434/api/tags`.

---

## 3. Semantic Embedding Model Setup (`multilingual-e5-small`)

Digital Afterlife strictly adheres to the principle of **Zero Silent Downloads**. Embedding weights are not downloaded in the background during installation or search queries.

### Option A: Download via Web UI
1. Open **Settings** in the Digital Afterlife web interface.
2. Under **Semantic Search & Vector Storage**, locate `multilingual-e5-small`.
3. Click **Download Weights**.
4. The backend streams the ONNX weights directly to `models/embeddings/multilingual-e5-small/`.

### Option B: Download via CLI
```bash
# Activate virtual environment
.\backend\.venv\Scripts\activate

# Run the download command
python -c "from backend.app.services.rag.model_manager import embedding_model_manager; embedding_model_manager.download_model('multilingual-e5-small')"
```

---

## 4. Local Speech-to-Text Model Setup (Whisper Base)

Similarly, Whisper speech weights are managed explicitly:
- **Location**: `models/whisper/base/`
- **Download via UI**: Open **Settings** > **Speech-to-Text Engine** > Click **Download Model** next to `base`.
- **Download via CLI**:
  ```bash
  python -c "from backend.app.services.speech.model_manager import model_manager; model_manager.download_model('base')"
  ```

---

## 5. Offline Fallback Behavior

If Ollama or the embedding model are not running:
- **Vault Operations**: Completely functional. Photo viewing, audio playback, document reading, and manual metadata editing work seamlessly.
- **Keyword Search**: Completely functional via SQLite fallback.
- **Ask Your Memories**: If Ollama is offline, the system retrieves and displays the verified raw source citations and excerpts without generating speculative prose.

