#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "Starting Digital Afterlife Backend (FastAPI on 127.0.0.1:8000)..."

if [ -f "backend/.venv/bin/python" ]; then
    PYTHON_BIN="backend/.venv/bin/python"
elif [ -f "backend/.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="backend/.venv/Scripts/python.exe"
else
    PYTHON_BIN="python"
fi

$PYTHON_BIN -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

