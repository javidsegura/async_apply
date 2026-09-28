"""Shared pytest fixtures: an isolated in-memory SQLite TestClient per test.

The app runs on Postgres; tests use SQLite so the suite needs no running
database. The models deliberately avoid Postgres-only types, so the two agree --
but anything engine-specific belongs in an integration test, not here.
"""

import itertools
from collections.abc import Generator

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db, models
from main import app
from services.asyncapply.auth import get_current_user
from services.asyncapply.settings import loader as asyncapply_settings_loader

_uid_seq = itertools.count(1)


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

    Also stashes the session factory on the client (`client.session_local`)
    so the `make_user` fixture can create rows against the exact same
    database the requests will hit.

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
    test_client.session_local = TestingSessionLocal
    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(client: TestClient):
    """Create a user row and make `client`'s requests authenticate as them.

    Real requests carry a Firebase bearer token; tests skip that entirely by
    overriding get_current_user directly, the same way the `client` fixture
    overrides get_db -- both dependencies resolve through the same
    request-scoped session, so a route that mutates `user` and commits via
    its own `db` param sees a consistent, single transaction.

    Returns a factory: make_user() for a regular user, make_user(role="admin")
    for an admin, make_user(token_budget_usd=0) etc. for any other field.
    Calling it again switches the client to a different, newly created user.

    Args:
        client: The TestClient this session is scoped to.

    Yields:
        A factory that creates a models.User row and returns it.
    """

    def _make(role: str = "user", **fields) -> models.User:
        db = client.session_local()
        n = next(_uid_seq)
        user = models.User(
            firebase_uid=f"test-uid-{n}",
            email=f"user{n}@example.com",
            role=role,
            **fields,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
        db.close()

        def _override(db: Session = Depends(get_db)) -> models.User:
            return db.get(models.User, user_id)

        app.dependency_overrides[get_current_user] = _override
        return user

    yield _make
    app.dependency_overrides.pop(get_current_user, None)
