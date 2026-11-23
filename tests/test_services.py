import pytest

SERVICE = {
    "name": "24/7 support",
    "description": "24/7 support with an 8 hour SLA",
    "suggested_price": "1500.00",
}


def _create(client, **overrides):
    payload = {**SERVICE, **overrides}
    response = client.post("/services", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_service_returns_201_with_payload(client):
    response = client.post("/services", json=SERVICE)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "24/7 support"
    assert body["description"] == "24/7 support with an 8 hour SLA"
    # Decimal is serialized as a string on purpose: no float rounding on money.
    assert body["suggested_price"] == "1500.00"


def test_created_service_is_persisted(client):
    created = _create(client)

    response = client.get(f"/services/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize("price", ["0", "0.00", "-10.00"])
def test_create_service_with_non_positive_price_returns_422(client, price):
    response = client.post("/services", json={**SERVICE, "suggested_price": price})

    assert response.status_code == 422


def test_create_service_without_description_returns_422(client):
    response = client.post(
        "/services", json={"name": "Support", "suggested_price": "100.00"}
    )

    assert response.status_code == 422


def test_create_service_with_too_long_name_returns_422(client):
    response = client.post("/services", json={**SERVICE, "name": "x" * 121})

    assert response.status_code == 422


def test_get_service_by_id(client):
    created = _create(client)

    response = client.get(f"/services/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["suggested_price"] == "1500.00"


def test_get_missing_service_returns_404(client):
    response = client.get("/services/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Service 9999 not found"


def test_update_service_changes_price_and_description(client):
    created = _create(client)

    response = client.patch(
        f"/services/{created['id']}",
        json={"description": "Updated description", "suggested_price": "1800.50"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated description"
    assert body["suggested_price"] == "1800.50"
    assert body["name"] == "24/7 support"  # untouched


def test_update_service_keeps_fields_that_were_not_sent(client):
    created = _create(client)

    response = client.patch(f"/services/{created['id']}", json={"suggested_price": "99.99"})

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_price"] == "99.99"
    assert body["description"] == "24/7 support with an 8 hour SLA"


def test_update_service_with_invalid_price_returns_422(client):
    created = _create(client)

    response = client.patch(f"/services/{created['id']}", json={"suggested_price": "-1"})

    assert response.status_code == 422


def test_update_missing_service_returns_404(client):
    response = client.patch("/services/9999", json={"description": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Service 9999 not found"
