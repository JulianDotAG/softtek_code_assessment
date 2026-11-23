SERVICE = {
    "name": "24/7 support",
    "description": "Phone and email support, 8 hour response time",
    "suggested_price": "1500.00",
}

RICH_SERVICE = {
    "name": "Custom integration",
    "description": "Integration with a third party system, quoted per project",
    "suggested_price": "12000.00",
}


def _customer(client, name="ACME Corp", email="contact@acme.com"):
    response = client.post("/customers", json={"name": name, "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def _service(client, payload=None):
    response = client.post("/services", json=payload or SERVICE)
    assert response.status_code == 201, response.text
    return response.json()


def _order(client, customer_id, service_id):
    response = client.post("/orders", json={"customer_id": customer_id, "service_id": service_id})
    assert response.status_code == 201, response.text
    return response.json()


def _cancel(client, order_id):
    response = client.post(f"/orders/{order_id}/cancel")
    assert response.status_code == 200, response.text


def _report(client, path):
    """Fetch a report, asserting 200 first so a missing route fails legibly."""
    response = client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


def test_last_sales_returns_an_empty_array_when_there_are_no_sales(client):
    response = client.get("/reports/last-sales")

    assert response.status_code == 200
    assert response.json() == []


def test_last_sales_returns_the_ten_most_recent(client):
    customer = _customer(client)
    service = _service(client)
    orders = [_order(client, customer["id"], service["id"]) for _ in range(12)]

    body = _report(client, "/reports/last-sales")

    assert len(body) == 10
    assert {row["id"] for row in body} == {order["id"] for order in orders[2:]}


def test_last_sales_is_ordered_newest_first(client):
    customer = _customer(client)
    service = _service(client)
    orders = [_order(client, customer["id"], service["id"]) for _ in range(3)]

    body = _report(client, "/reports/last-sales")

    # Every row shares created_at inside one test transaction, so the tie-breaker
    # (id DESC) is what makes "newest first" deterministic.
    assert [row["id"] for row in body] == [orders[2]["id"], orders[1]["id"], orders[0]["id"]]
    assert [row["created_at"] for row in body] == sorted(
        (row["created_at"] for row in body), reverse=True
    )


def test_last_sales_excludes_cancelled_orders(client):
    customer = _customer(client)
    service = _service(client)
    kept = _order(client, customer["id"], service["id"])
    cancelled = _order(client, customer["id"], service["id"])
    _cancel(client, cancelled["id"])

    body = _report(client, "/reports/last-sales")

    assert [row["id"] for row in body] == [kept["id"]]
    assert cancelled["folio"] not in {row["folio"] for row in body}


def test_last_sales_fills_the_window_after_removing_cancelled_orders(client):
    customer = _customer(client)
    service = _service(client)
    orders = [_order(client, customer["id"], service["id"]) for _ in range(12)]
    _cancel(client, orders[-1]["id"])

    body = _report(client, "/reports/last-sales")

    # 12 orders, one cancelled: the limit is applied after excluding it, so ten remain.
    assert len(body) == 10
    assert orders[-1]["id"] not in {row["id"] for row in body}


def test_last_sales_has_the_required_fields(client):
    customer = _customer(client)
    service = _service(client)
    _order(client, customer["id"], service["id"])

    row = _report(client, "/reports/last-sales")[0]

    assert row["customer_name"] == "ACME Corp"
    assert row["service_description"] == SERVICE["description"]
    assert row["amount"] == "1500.00"
    assert row["folio"].isdigit()
    assert row["id"] > 0
    assert "created_at" in row


def test_sales_by_customer_totals_and_counts(client):
    acme = _customer(client, "ACME Corp", "contact@acme.com")
    globex = _customer(client, "Globex Corporation", "billing@globex.com")
    service = _service(client)
    rich = _service(client, RICH_SERVICE)

    _order(client, acme["id"], service["id"])
    _order(client, acme["id"], service["id"])
    _order(client, globex["id"], rich["id"])

    body = _report(client, "/reports/sales-by-customer")

    assert body == [
        {
            "customer_id": globex["id"],
            "customer_name": "Globex Corporation",
            "order_count": 1,
            "total": "12000.00",
        },
        {
            "customer_id": acme["id"],
            "customer_name": "ACME Corp",
            "order_count": 2,
            "total": "3000.00",
        },
    ]


def test_sales_by_customer_includes_customers_without_sales(client):
    with_sales = _customer(client, "ACME Corp", "contact@acme.com")
    idle = _customer(client, "Soylent Foods", "orders@soylentfoods.com")
    service = _service(client)
    _order(client, with_sales["id"], service["id"])

    body = _report(client, "/reports/sales-by-customer")

    assert body[0]["customer_id"] == with_sales["id"]
    assert body[1] == {
        "customer_id": idle["id"],
        "customer_name": "Soylent Foods",
        "order_count": 0,
        "total": "0.00",
    }


def test_sales_by_customer_is_ordered_by_total_desc(client):
    small = _customer(client, "Initech", "accounts@initech.com")
    big = _customer(client, "Globex Corporation", "billing@globex.com")
    middle = _customer(client, "Stark Industries", "procurement@stark.com")
    service = _service(client)
    rich = _service(client, RICH_SERVICE)

    _order(client, small["id"], service["id"])
    _order(client, big["id"], rich["id"])
    _order(client, middle["id"], service["id"])
    _order(client, middle["id"], service["id"])

    totals = [row["total"] for row in _report(client, "/reports/sales-by-customer")]

    assert totals == ["12000.00", "3000.00", "1500.00"]


def test_sales_by_customer_excludes_cancelled_orders(client):
    customer = _customer(client)
    service = _service(client)
    kept = _order(client, customer["id"], service["id"])
    cancelled = _order(client, customer["id"], service["id"])
    _cancel(client, cancelled["id"])

    row = _report(client, "/reports/sales-by-customer")[0]

    assert row["customer_id"] == customer["id"]
    assert row["order_count"] == 1
    assert row["total"] == kept["amount"]


def test_sales_by_customer_reports_zero_when_every_order_was_cancelled(client):
    customer = _customer(client)
    service = _service(client)
    order = _order(client, customer["id"], service["id"])
    _cancel(client, order["id"])

    row = _report(client, "/reports/sales-by-customer")[0]

    assert row["order_count"] == 0
    assert row["total"] == "0.00"


def test_sales_by_customer_amounts_are_strings(client):
    customer = _customer(client)
    service = _service(client)
    _order(client, customer["id"], service["id"])

    row = _report(client, "/reports/sales-by-customer")[0]

    assert isinstance(row["total"], str)
    assert isinstance(row["order_count"], int)
