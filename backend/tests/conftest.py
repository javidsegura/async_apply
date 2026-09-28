"""Shared pytest fixtures: an isolated in-memory SQLite TestClient per test.

The app runs on Postgres; tests use SQLite so the suite needs no running
database. The models deliberately avoid Postgres-only types, so the two agree --
but anything engine-specific belongs in an integration test, not here.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from services.asyncapply.settings import loader as asyncapply_settings_loader


@pytest.fixture(autouse=True)
def isolated_asyncapply_settings_db(monkeypatch: pytest.MonkeyPatch):
    """Point get_settings() at a throwaway SQLite DB for every test.

    get_settings() opens its own session rather than taking one as a
    parameter -- it is also called from the worker and llm.py, outside any
    request -- so it is not covered by the `client` fixture's get_db
    override below. Without this, any test that reaches get_settings()
    hits the real Postgres configured in .env.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(asyncapply_settings_loader, "SessionLocal", session_factory)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a TestClient backed by a fresh in-memory SQLite database.

    Yields:
        TestClient: A client with the get_db dependency overridden.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Deliberately not used as a context manager: that would fire the app's
    # startup event, which recovers orphaned work against the real database.
    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
