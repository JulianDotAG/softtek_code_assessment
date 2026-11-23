from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Engine bound to a test database rebuilt from the real migrations.

    The schema reset is destructive, so the URL is validated first: a mistyped
    TEST_DATABASE_URL must never be able to wipe a development database.
    """
    url = settings.test_database_url
    database_name = url.rsplit("/", 1)[-1]
    if not database_name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run tests against {database_name!r}: "
            "TEST_DATABASE_URL must point to a database whose name ends with '_test'"
        )

    eng = create_engine(url, pool_pre_ping=True)
    with eng.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()

    # Applying the migrations instead of create_all() keeps them covered by the suite:
    # if a migration is broken, every test fails here.
    alembic_config = AlembicConfig("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(alembic_config, "head")

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
