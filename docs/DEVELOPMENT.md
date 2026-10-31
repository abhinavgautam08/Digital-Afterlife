# Development & Maintenance Guide

**Project**: Digital Afterlife – Memory Keeper  
**Version**: 0.1.0  
**Phase**: Phase 1: Foundation & Architecture  

---

## 1. Project Organization

```
Digital Afterlife/
├── backend/
│   ├── app/
│   │   ├── api/            # API Route controllers (no domain logic)
│   │   ├── core/           # Config, logging, security & encryption abstraction
│   │   ├── database/       # SQLAlchemy engine, sessionmaker, base
│   │   ├── models/         # SQLite database models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Domain services (Memory, Person, Storage, System, Ollama)
│   │   ├── __init__.py
│   │   └── main.py         # FastAPI application entry point
│   ├── tests/              # Pytest test suite (16 tests)
│   ├── requirements.txt    # Python backend dependencies
│   └── .venv/              # Isolated virtual environment
├── frontend/
│   ├── src/
│   │   ├── assets/         # Static assets
│   │   ├── components/     # Reusable UI components (Navbar, Modals)
│   │   ├── pages/          # 5 Core views (Dashboard, Vault, People, AIStudio, Settings)
│   │   ├── services/       # Typed REST API client
│   │   ├── types/          # TypeScript interfaces
│   │   ├── App.tsx         # Root app layout & routing
│   │   ├── index.css       # Tailwind theme & glassmorphism utilities
│   │   └── main.tsx        # React DOM entry
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts      # Vite bundler & backend reverse proxy
├── data/
│   ├── digital_afterlife.db # Main SQLite database (WAL mode)
│   ├── memories/           # Secure local storage root for memory files
│   └── thumbnails/         # Cache directory for media previews
├── docs/                   # Architectural, API, and Phase 1 documentation
├── scripts/                # Development & startup scripts (Windows & POSIX)
├── .env.example            # Environment configuration template
├── pyproject.toml          # Pytest configuration
└── README.md               # User & operator introduction
```

---

## 2. Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 20+ (with npm)
- Ollama (optional, for local AI features)

### Backend Setup
```bash
# 1. Create and activate virtual environment
python -m venv backend/.venv

# Windows
backend\.venv\Scripts\activate

# Linux / macOS
source backend/.venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Initialize SQLite database schema
python scripts/init_db.py
```

### Frontend Setup
```bash
cd frontend
npm install
```

---

## 3. Running Development Servers

### Option A: Run Using Automation Scripts
- **Windows**:
  - Run `scripts\run_backend.bat` in one terminal
  - Run `scripts\run_frontend.bat` in another terminal
- **Linux / macOS**:
  - Run `bash scripts/run_backend.sh`
  - Run `bash scripts/run_frontend.sh`

### Option B: Run Directly
**Backend**:
```bash
backend\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend**:
```bash
cd frontend
npm run dev
```
Open your browser to `http://127.0.0.1:5173`.

---

## 4. Running the Test Suite

The test suite exercises:
- Database initialization
- File storage containment & path traversal protection
- Extension & MIME type whitelisting
- File size boundary enforcement
- Memory ingestion and duplicate prevention (SHA-256)
- Memory deletion & physical cleanup
- People directory and memory association
- Graceful offline fallback when Ollama is unavailable
- Phase 1 encryption abstraction contracts

Run pytest from the project root:
```bash
backend\.venv\Scripts\pytest.exe -v
```

---

## 5. Building the Frontend for Production

Verify TypeScript compilation and generate the optimized production assets:
```bash
cd frontend
npm run build
```
Assets are generated in `frontend/dist/`.

