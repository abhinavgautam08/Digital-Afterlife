"""
Pytest fixtures and configuration.
Uses an isolated in-memory SQLite database and isolated temp storage.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.services.storage_service import storage_service


@pytest.fixture(scope="session")
def test_dirs():
    """Create isolated temporary data and storage directories for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_digital_afterlife_")
    temp_path = Path(temp_dir)
    memories_path = temp_path / "memories"
    memories_path.mkdir(parents=True, exist_ok=True)

    original_storage = storage_service.storage_dir
    storage_service.storage_dir = memories_path

    yield temp_path, memories_path

    storage_service.storage_dir = original_storage
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_db():
    """Provides an isolated in-memory SQLite database per test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture(scope="function")
def client(test_db):
    """Provides a TestClient with dependency override for get_db."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
