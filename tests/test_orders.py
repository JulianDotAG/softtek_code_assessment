"""`POST /orders`, `GET /orders/{order_id}` and `POST /orders/{order_id}/cancel`.

An order is a sale of one service to one customer, and it freezes what the service looked
like at that moment: `service_description` and `amount` are copied by value, so a later
`PATCH /services/{id}` cannot rewrite history — while orders created afterwards do take the
new price. The client never sets the amount; it always comes from the service.

Every order gets a sequence-backed folio, six digits, unique across the table.

Cancelling stamps `cancelled_at` and keeps all the data. A second cancel is a 409 because
the caller still believes the order is alive; an unknown id is a 404.
"""


def test_create_order_returns_the_service_snapshot(customer, service, create_order):
    order = create_order(customer["id"], service["id"])

    assert order["customer_id"] == customer["id"]
    assert order["service_id"] == service["id"]
    assert order["service_description"] == service["description"]
    assert order["amount"] == "1500.00"
    assert order["cancelled_at"] is None
    # The customer is nested and trimmed; the service stays an id, its data is in the snapshot.
    assert order["customer"] == {"id": customer["id"], "name": "ACME Corp"}


def test_created_order_can_be_fetched_by_id(order, get):
    assert get(f"/orders/{order['id']}") == order


def test_folio_is_six_digits(order):
    assert order["folio"].isdigit()
    assert len(order["folio"]) == 6


def test_folio_increments_by_one(create_order, order, customer, service):
    second = create_order(customer["id"], service["id"])

    assert int(second["folio"]) == int(order["folio"]) + 1
    assert second["folio"] not in {order["folio"]}


def test_client_cannot_set_the_amount(create_order, customer, service):
    """`amount` is not a field of the request: the service price always wins."""
    order = create_order(customer["id"], service["id"], amount="1.00")

    assert order["amount"] == "1500.00"


def test_editing_the_service_does_not_change_existing_orders(order, service, client, get):
    response = client.patch(
        f"/services/{service['id']}",
        json={"description": "Rewritten", "suggested_price": "9999.00"},
    )
    assert response.status_code == 200

    body = get(f"/orders/{order['id']}")

    assert body["amount"] == "1500.00"
    assert body["service_description"] == service["description"]


def test_orders_created_after_the_edit_use_the_new_price(create_order, order, service, client, get):
    """The other half of the same rule: the snapshot is a copy, not a stale link."""
    client.patch(f"/services/{service['id']}", json={"suggested_price": "9999.00"})

    after = create_order(order["customer_id"], service["id"])

    assert after["amount"] == "9999.00"
    assert get(f"/orders/{order['id']}")["amount"] == "1500.00"


def test_unknown_customer_returns_404(service, client):
    response = client.post("/orders", json={"customer_id": 9999, "service_id": service["id"]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer 9999 not found"}


def test_unknown_service_returns_404(customer, client):
    response = client.post("/orders", json={"customer_id": customer["id"], "service_id": 9999})

    assert response.status_code == 404
    assert response.json() == {"detail": "Service 9999 not found"}


def test_missing_customer_id_returns_422(service, client):
    response = client.post("/orders", json={"service_id": service["id"]})

    assert response.status_code == 422


def test_missing_service_id_returns_422(customer, client):
    response = client.post("/orders", json={"customer_id": customer["id"]})

    assert response.status_code == 422


def test_missing_order_returns_404(client):
    response = client.get("/orders/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Order 9999 not found"}


def test_cancel_stamps_cancelled_at_and_keeps_the_data(order, client, get):
    response = client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["cancelled_at"] is not None
    assert body["amount"] == order["amount"]
    assert body["folio"] == order["folio"]
    assert body["service_description"] == order["service_description"]
    assert get(f"/orders/{order['id']}") == body


def test_cancelling_twice_returns_409(order, client):
    client.post(f"/orders/{order['id']}/cancel")

    response = client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 409
    assert response.json() == {"detail": f"Order {order['id']} is already cancelled"}


def test_cancelling_one_order_leaves_the_others_alone(order, create_order, client, get):
    other = create_order(order["customer_id"], order["service_id"])

    client.post(f"/orders/{order['id']}/cancel")

    assert get(f"/orders/{order['id']}")["cancelled_at"] is not None
    assert get(f"/orders/{other['id']}")["cancelled_at"] is None


def test_cancel_missing_order_returns_404(client):
    response = client.post("/orders/9999/cancel")

    assert response.status_code == 404
    assert response.json() == {"detail": "Order 9999 not found"}
