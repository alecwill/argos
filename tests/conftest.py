"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CACHE_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a temporary data directory for tests."""
    return tmp_path_factory.mktemp("data")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    from pet_persona.db.session import get_engine, init_db
    from sqlmodel import Session, SQLModel

    # Create in-memory database
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="function")
def repository(db_session):
    """Create a repository with test database session."""
    from pet_persona.db.repo import Repository
    return Repository(db_session)


@pytest.fixture
def sample_user(repository):
    """Create a sample user for testing."""
    return repository.create_user("test_user", "test@example.com")


@pytest.fixture
def sample_pet(repository, sample_user):
    """Create a sample pet for testing."""
    return repository.create_pet(
        user_id=sample_user.id,
        name="TestDog",
        species="dog",
        breed="Golden Retriever",
        age=3,
        sex="male",
    )
