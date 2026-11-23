from collections.abc import Callable, Iterator

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


# --- Fixtures for the resources every test file needs -------------------------------
# Factories are used when a test needs two of something, the plain fixtures for the
# common case. Assertions live in the factories, so a setup failure names the setup.


@pytest.fixture
def create_customer(client: TestClient) -> Callable[..., dict]:
    def _create(name: str = "ACME Corp", email: str = "contact@acme.com") -> dict:
        response = client.post("/customers", json={"name": name, "email": email})
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def create_service(client: TestClient) -> Callable[..., dict]:
    def _create(**overrides: str) -> dict:
        payload = {
            "name": "24/7 support",
            "description": "Phone and email support, 8 hour response time",
            "suggested_price": "1500.00",
            **overrides,
        }
        response = client.post("/services", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def create_order(client: TestClient) -> Callable[..., dict]:
    def _create(customer_id: int, service_id: int, **extra: str) -> dict:
        payload = {"customer_id": customer_id, "service_id": service_id, **extra}
        response = client.post("/orders", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def customer(create_customer: Callable[..., dict]) -> dict:
    """The default customer: ACME Corp, contact@acme.com."""
    return create_customer()


@pytest.fixture
def service(create_service: Callable[..., dict]) -> dict:
    """The default service: 24/7 support, 1500.00."""
    return create_service()


@pytest.fixture
def order(create_order: Callable[..., dict], customer: dict, service: dict) -> dict:
    """A placed order of that customer on that service."""
    return create_order(customer["id"], service["id"])


@pytest.fixture
def get(client: TestClient) -> Callable[[str], dict]:
    """GET that asserts 200 first, so a missing route fails on the contract, not on a KeyError."""

    def _get(path: str) -> dict:
        response = client.get(path)
        assert response.status_code == 200, response.text
        return response.json()

    return _get
