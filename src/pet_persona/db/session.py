"""Database session management for Pet Persona AI."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from pet_persona.config import get_settings
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)

# Global engine instance
_engine = None


def get_engine():
    """Get or create the database engine."""
    global _engine

    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url

        # Ensure data directory exists for SQLite
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if not db_path.startswith("/"):
                # Relative path - make it relative to base_dir
                db_path = settings.base_dir / db_path
            else:
                db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{db_path}"

        logger.debug(f"Creating database engine: {db_url}")
        _engine = create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )

    return _engine


def init_db() -> None:
    """Initialize the database, creating all tables."""
    engine = get_engine()
    logger.info("Initializing database...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized successfully")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session as a context manager."""
    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_session_direct() -> Session:
    """Get a database session directly (caller must manage lifecycle)."""
    engine = get_engine()
    return Session(engine)
