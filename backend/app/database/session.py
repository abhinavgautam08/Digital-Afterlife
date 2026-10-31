"""
Database engine, sessionmaker, and dependency injection.
Configured for SQLite with WAL mode, foreign key enforcement, and migration-safe table evolution.
"""
from typing import Generator
import uuid
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from backend.app.core.config import settings
from backend.app.core.logging import logger

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
    future=True
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable SQLite Foreign Key constraints and WAL mode for reliability."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception as e:
        logger.warning(f"Could not apply SQLite pragmas: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations(connection) -> None:
    """
    Applies non-destructive schema migrations for existing databases.
    Adds Phase 2 columns to 'memories' and 'memory_tags' if they are missing.
    """
    try:
        # Check columns in memories table
        result = connection.execute(text("PRAGMA table_info(memories)")).fetchall()
        existing_cols = {row[1] for row in result}

        if existing_cols:
            phase2_columns = [
                ("file_hash", "VARCHAR(64)"),
                ("width", "INTEGER"),
                ("height", "INTEGER"),
                ("duration_seconds", "FLOAT"),
                ("extracted_text", "TEXT"),
                ("thumbnail_path", "VARCHAR(500)"),
                ("original_created_at", "DATETIME"),
                ("location", "VARCHAR(255)"),
                ("processing_error", "TEXT"),
            ]

            for col_name, col_type in phase2_columns:
                if col_name not in existing_cols:
                    connection.execute(text(f"ALTER TABLE memories ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"Migrated memories table: added column '{col_name}' ({col_type})")

            # Sync file_hash with sha256_hash for pre-existing records
            if "sha256_hash" in existing_cols and "file_hash" in existing_cols:
                connection.execute(text("UPDATE memories SET file_hash = sha256_hash WHERE file_hash IS NULL"))

            # Create partial unique index to prevent concurrent duplicate uploads
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_memories_file_hash ON memories(file_hash) WHERE file_hash IS NOT NULL"))

        # Check columns in memory_tags table
        tag_result = connection.execute(text("PRAGMA table_info(memory_tags)")).fetchall()
        existing_tag_cols = {row[1] for row in tag_result}
        if existing_tag_cols and "created_at" not in existing_tag_cols:
            connection.execute(text("ALTER TABLE memory_tags ADD COLUMN created_at DATETIME"))
            logger.info("Migrated memory_tags table: added column 'created_at'")

        # Check columns in transcripts table (Phase 3 Extensions)
        transcript_result = connection.execute(text("PRAGMA table_info(transcripts)")).fetchall()
        existing_transcript_cols = {row[1] for row in transcript_result}
        if existing_transcript_cols:
            phase3_transcript_cols = [
                ("detected_language", "VARCHAR(10)"),
                ("model_name", "VARCHAR(50)"),
                ("processing_duration", "FLOAT"),
                ("updated_at", "DATETIME"),
            ]
            for col_name, col_type in phase3_transcript_cols:
                if col_name not in existing_transcript_cols:
                    connection.execute(text(f"ALTER TABLE transcripts ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"Migrated transcripts table: added column '{col_name}' ({col_type})")
            if "updated_at" in existing_transcript_cols:
                connection.execute(text("UPDATE transcripts SET updated_at = created_at WHERE updated_at IS NULL"))

    except Exception as e:
        logger.warning(f"Migration check completed with notice: {e}")


def seed_default_tags(db: Session) -> None:
    """Seeds default suggested tags for family heritage preservation."""
    from backend.app.models.tag import MemoryTag

    default_tags = [
        "Childhood",
        "Family",
        "Celebration",
        "Travel",
        "Childhood Memories",
        "Important Events",
        "Personal Letters",
        "Traditions"
    ]

    for name in default_tags:
        exists = db.query(MemoryTag).filter(MemoryTag.name == name.lower()).first()
        if not exists:
            db.add(MemoryTag(id=str(uuid.uuid4()), name=name.lower()))
    db.commit()


def init_db() -> None:
    """Initialize database tables and run schema migrations."""
    from backend.app.database.base import Base
    import backend.app.models.memory  # noqa
    import backend.app.models.person  # noqa
    import backend.app.models.transcript  # noqa
    import backend.app.models.tag  # noqa
    import backend.app.models.transcription_job  # noqa
    import backend.app.models.speaker  # noqa
    import backend.app.models.indexing_job  # noqa
    import backend.app.models.storytelling  # noqa

    # Create tables if not existing
    Base.metadata.create_all(bind=engine)

    # Apply SQLite column additions if upgrading existing DB
    with engine.begin() as conn:
        run_migrations(conn)

    # Seed default taxonomy tags
    db = SessionLocal()
    try:
        seed_default_tags(db)
    finally:
        db.close()

    logger.info("Database tables and Phase 3 schema initialized successfully.")
