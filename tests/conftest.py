from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Engine bound to the dedicated test database.

    The destructive part of the harness (schema reset, migrations) will hang off this
    fixture. Until that exists, fail loudly if the URL does not look like a test database:
    a mistyped URL here would otherwise wipe a development database later.
    """
    url = settings.test_database_url
    database_name = url.rsplit("/", 1)[-1]
    if not database_name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run tests against {database_name!r}: "
            "TEST_DATABASE_URL must point to a database whose name ends with '_test'"
        )

    eng = create_engine(url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """One outer transaction per test; the application's commit() becomes a savepoint.

    This is what makes tests isolated without truncating tables between them.
    """
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    database_session = factory()
    try:
        yield database_session
    finally:
        database_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """HTTP client with the app's session dependency replaced by the test session."""
    from app.database import get_session
    from app.main import app

    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
