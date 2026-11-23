"""`POST`, `GET` and `PATCH /services/{service_id}`.

A service is the catalogue: orders copy its description and price when they are created.
The price contract is the column itself — `NUMERIC(12,2)` and strictly positive — so
anything the column cannot hold is rejected at the edge with a 422 instead of being
rounded by the database.

`PATCH` touches only the fields it receives. Omitting a field keeps it, an empty body
changes nothing, an unknown field is ignored, and an explicit `null` is rejected: it would
otherwise reach the `UPDATE` and violate `NOT NULL`.
"""

import pytest


def test_create_service_returns_the_stored_service(client):
    response = client.post(
        "/services",
        json={
            "name": "24/7 support",
            "description": "Phone and email support, 8 hour response time",
            "suggested_price": "1500.00",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "24/7 support"
    assert body["description"] == "Phone and email support, 8 hour response time"
    # Decimal is serialized as a string on purpose: no float rounding on money.
    assert body["suggested_price"] == "1500.00"
    assert body["created_at"] == body["updated_at"]


def test_created_service_can_be_fetched_by_id(create_service, get):
    created = create_service()

    assert get(f"/services/{created['id']}") == created


def test_a_cent_is_a_valid_price(create_service):
    """`gt=0` rejects zero and negatives, so the smallest valid price still has to pass."""
    assert create_service(suggested_price="0.01")["suggested_price"] == "0.01"


@pytest.mark.parametrize(
    ("price", "why"),
    [
        ("0", "zero"),
        ("0.00", "zero with decimals"),
        ("-10.00", "negative"),
        ("1.234", "more decimals than the column holds"),
        ("12345678901.00", "more whole digits than the column holds"),
    ],
)
def test_a_price_outside_the_column_contract_returns_422(client, price, why):
    response = client.post(
        "/services",
        json={"name": "Support", "description": "d", "suggested_price": price},
    )

    assert response.status_code == 422, why


def test_missing_price_returns_422(client):
    response = client.post("/services", json={"name": "Support", "description": "d"})

    assert response.status_code == 422


def test_missing_description_returns_422(client):
    response = client.post("/services", json={"name": "Support", "suggested_price": "100.00"})

    assert response.status_code == 422


def test_name_over_120_characters_returns_422(client):
    response = client.post(
        "/services",
        json={"name": "x" * 121, "description": "d", "suggested_price": "100.00"},
    )

    assert response.status_code == 422


def test_missing_service_returns_404(client):
    response = client.get("/services/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Service 9999 not found"}


def test_patch_updates_only_the_fields_it_receives(service, client, get):
    response = client.patch(
        f"/services/{service['id']}",
        json={"suggested_price": "1800.50"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_price"] == "1800.50"
    assert body["name"] == service["name"]
    assert body["description"] == service["description"]
    assert get(f"/services/{service['id']}") == body


def test_patch_updates_several_fields_at_once(service, client):
    response = client.patch(
        f"/services/{service['id']}",
        json={"name": "Priority support", "description": "Updated description"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Priority support"
    assert body["description"] == "Updated description"
    assert body["suggested_price"] == service["suggested_price"]


def test_patch_with_an_empty_body_changes_nothing(service, client, get):
    response = client.patch(f"/services/{service['id']}", json={})

    assert response.status_code == 200
    assert response.json() == service
    assert get(f"/services/{service['id']}") == service


def test_patch_ignores_unknown_fields(service, client):
    response = client.patch(f"/services/{service['id']}", json={"colour": "red"})

    assert response.status_code == 200
    assert response.json() == service


@pytest.mark.parametrize("field", ["name", "description", "suggested_price"])
def test_patch_with_an_explicit_null_returns_422(service, client, get, field):
    """`null` is not "leave it alone": it would reach the UPDATE and break NOT NULL."""
    response = client.patch(f"/services/{service['id']}", json={field: None})

    assert response.status_code == 422
    assert "cannot be null" in response.text
    assert get(f"/services/{service['id']}") == service


def test_patch_with_an_invalid_price_returns_422(service, client, get):
    response = client.patch(f"/services/{service['id']}", json={"suggested_price": "-1"})

    assert response.status_code == 422
    assert get(f"/services/{service['id']}") == service


def test_patch_missing_service_returns_404(client):
    response = client.patch("/services/9999", json={"description": "x"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Service 9999 not found"}
