@echo off
echo Starting Digital Afterlife Backend (FastAPI on 127.0.0.1:8000)...
cd /d "%~dp0\.."

if not exist "backend\.venv\Scripts\python.exe" (
    echo Python virtual environment not found in backend\.venv.
    echo Please create it using: python -m venv backend\.venv
    exit /b 1
)

backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

