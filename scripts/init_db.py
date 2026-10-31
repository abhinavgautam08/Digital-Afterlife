"""
Database initialization script.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database.session import init_db
from backend.app.core.logging import logger

if __name__ == "__main__":
    logger.info("Initializing Digital Afterlife SQLite database...")
    init_db()
    logger.info("Database schema initialized successfully.")

