from sqlalchemy import text


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_test_database_is_reachable(session):
    """Guards the fixture chain: test database -> engine -> session."""
    assert session.execute(text("select 1")).scalar_one() == 1
