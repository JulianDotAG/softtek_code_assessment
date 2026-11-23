SERVICE = {
    "name": "24/7 support",
    "description": "Phone and email support, 8 hour response time",
    "suggested_price": "1500.00",
}


def _create_customer(client, name="ACME Corp", email="contact@acme.com"):
    response = client.post("/customers", json={"name": name, "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def _create_service(client, **overrides):
    response = client.post("/services", json={**SERVICE, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def _create_order(client, customer_id, service_id, **extra):
    payload = {"customer_id": customer_id, "service_id": service_id, **extra}
    response = client.post("/orders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_order_returns_201_with_the_service_snapshot(client):
    customer = _create_customer(client)
    service = _create_service(client)

    response = client.post(
        "/orders", json={"customer_id": customer["id"], "service_id": service["id"]}
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["customer_id"] == customer["id"]
    assert body["service_id"] == service["id"]
    assert body["service_description"] == SERVICE["description"]
    assert body["amount"] == "1500.00"
    assert body["cancelled_at"] is None
    # The customer is nested; the service is not, its data already lives in the snapshot.
    assert body["customer"] == {"id": customer["id"], "name": "ACME Corp"}


def test_folio_is_six_digits(client):
    customer = _create_customer(client)
    service = _create_service(client)

    order = _create_order(client, customer["id"], service["id"])

    assert order["folio"].isdigit()
    assert len(order["folio"]) == 6


def test_folio_increments_by_one(client):
    customer = _create_customer(client)
    service = _create_service(client)

    first = _create_order(client, customer["id"], service["id"])
    second = _create_order(client, customer["id"], service["id"])

    assert int(second["folio"]) == int(first["folio"]) + 1


def test_editing_the_service_does_not_change_existing_orders(client):
    """The core business rule: the order freezes the service data at creation time."""
    customer = _create_customer(client)
    service = _create_service(client)
    order = _create_order(client, customer["id"], service["id"])

    patch = client.patch(
        f"/services/{service['id']}",
        json={"description": "Rewritten", "suggested_price": "9999.00"},
    )
    assert patch.status_code == 200

    response = client.get(f"/orders/{order['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "1500.00"
    assert body["service_description"] == SERVICE["description"]


def test_orders_created_after_the_edit_use_the_new_price(client):
    """The other half of the same rule: the snapshot is a copy, not a link that never updates."""
    customer = _create_customer(client)
    service = _create_service(client)
    before = _create_order(client, customer["id"], service["id"])

    client.patch(f"/services/{service['id']}", json={"suggested_price": "9999.00"})
    after = _create_order(client, customer["id"], service["id"])

    assert after["amount"] == "9999.00"
    assert client.get(f"/orders/{before['id']}").json()["amount"] == "1500.00"


def test_created_order_is_persisted(client):
    customer = _create_customer(client)
    service = _create_service(client)
    created = _create_order(client, customer["id"], service["id"])

    response = client.get(f"/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_client_cannot_set_the_amount(client):
    customer = _create_customer(client)
    service = _create_service(client)

    order = _create_order(client, customer["id"], service["id"], amount="1.00")

    assert order["amount"] == "1500.00"


def test_create_order_with_unknown_customer_returns_404(client):
    service = _create_service(client)

    response = client.post("/orders", json={"customer_id": 9999, "service_id": service["id"]})

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer 9999 not found"


def test_create_order_with_unknown_service_returns_404(client):
    customer = _create_customer(client)

    response = client.post("/orders", json={"customer_id": customer["id"], "service_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Service 9999 not found"


def test_create_order_without_customer_id_returns_422(client):
    service = _create_service(client)

    response = client.post("/orders", json={"service_id": service["id"]})

    assert response.status_code == 422


def test_create_order_without_service_id_returns_422(client):
    customer = _create_customer(client)

    response = client.post("/orders", json={"customer_id": customer["id"]})

    assert response.status_code == 422


def test_get_missing_order_returns_404(client):
    response = client.get("/orders/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order 9999 not found"


def test_cancel_order_sets_cancelled_at(client):
    customer = _create_customer(client)
    service = _create_service(client)
    order = _create_order(client, customer["id"], service["id"])

    response = client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["cancelled_at"] is not None
    assert body["amount"] == "1500.00"


def test_cancelling_an_already_cancelled_order_returns_409(client):
    customer = _create_customer(client)
    service = _create_service(client)
    order = _create_order(client, customer["id"], service["id"])
    client.post(f"/orders/{order['id']}/cancel")

    response = client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == f"Order {order['id']} is already cancelled"


def test_cancel_missing_order_returns_404(client):
    response = client.post("/orders/9999/cancel")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order 9999 not found"


def test_cancelling_one_order_leaves_the_others_alone(client):
    customer = _create_customer(client)
    service = _create_service(client)
    cancelled = _create_order(client, customer["id"], service["id"])
    untouched = _create_order(client, customer["id"], service["id"])

    client.post(f"/orders/{cancelled['id']}/cancel")

    assert client.get(f"/orders/{cancelled['id']}").json()["cancelled_at"] is not None
    assert client.get(f"/orders/{untouched['id']}").json()["cancelled_at"] is None


def test_cancelled_order_keeps_its_snapshot(client):
    customer = _create_customer(client)
    service = _create_service(client)
    order = _create_order(client, customer["id"], service["id"])

    client.post(f"/orders/{order['id']}/cancel")
    body = client.get(f"/orders/{order['id']}").json()

    assert body["folio"] == order["folio"]
    assert body["amount"] == "1500.00"
    assert body["service_description"] == SERVICE["description"]
