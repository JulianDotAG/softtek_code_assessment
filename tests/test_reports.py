"""`GET /reports/last-sales` and `GET /reports/sales-by-customer`.

Both reports read the amount frozen on the order, never the current service price, and both
exclude cancelled orders.

`last-sales` is a flat array of at most ten rows, newest first. Ten is a ceiling and it is
applied after the cancelled orders are removed, so a cancellation never shrinks the window.

`sales-by-customer` covers every customer, including one with no sales at all
(`order_count: 0, total: "0.00"`), ordered by accumulated total, biggest first, with the
customer id as tie-breaker.
"""

RICH_SERVICE = {"suggested_price": "12000.00"}


def test_last_sales_of_a_database_without_sales_is_an_empty_array(client):
    response = client.get("/reports/last-sales")

    assert response.status_code == 200
    assert response.json() == []


def test_last_sales_returns_the_ten_most_recent(create_order, customer, service, get):
    orders = [create_order(customer["id"], service["id"]) for _ in range(12)]

    body = get("/reports/last-sales")

    assert len(body) == 10
    assert {row["id"] for row in body} == {order["id"] for order in orders[2:]}


def test_last_sales_returns_everything_when_there_are_fewer_than_ten(
    create_order, customer, service, get
):
    orders = [create_order(customer["id"], service["id"]) for _ in range(3)]

    assert [row["id"] for row in get("/reports/last-sales")] == [
        orders[2]["id"],
        orders[1]["id"],
        orders[0]["id"],
    ]


def test_last_sales_is_ordered_newest_first(create_order, customer, service, get):
    orders = [create_order(customer["id"], service["id"]) for _ in range(3)]

    body = get("/reports/last-sales")

    # Every row shares created_at inside one test transaction, so the id tie-breaker is
    # what makes "newest first" deterministic.
    assert [row["id"] for row in body] == [orders[2]["id"], orders[1]["id"], orders[0]["id"]]
    assert [row["created_at"] for row in body] == sorted(
        (row["created_at"] for row in body), reverse=True
    )


def test_last_sales_leaves_out_cancelled_orders(order, create_order, client, get):
    cancelled = create_order(order["customer_id"], order["service_id"])
    client.post(f"/orders/{cancelled['id']}/cancel")

    body = get("/reports/last-sales")

    assert [row["id"] for row in body] == [order["id"]]
    assert cancelled["folio"] not in {row["folio"] for row in body}


def test_last_sales_fills_the_window_after_removing_cancelled_orders(
    create_order, customer, service, client, get
):
    orders = [create_order(customer["id"], service["id"]) for _ in range(12)]
    client.post(f"/orders/{orders[-1]['id']}/cancel")

    body = get("/reports/last-sales")

    assert len(body) == 10
    assert orders[-1]["id"] not in {row["id"] for row in body}


def test_a_last_sales_row_has_the_sale_fields(order, get):
    row = get("/reports/last-sales")[0]

    assert row == {
        "id": order["id"],
        "folio": order["folio"],
        "customer_name": "ACME Corp",
        "service_description": order["service_description"],
        "amount": "1500.00",
        "created_at": order["created_at"],
    }


def test_sales_by_customer_reports_count_and_total(
    create_customer, create_service, create_order, service, order, get
):
    globex = create_customer("Globex Corporation", "billing@globex.com")
    rich = create_service(**RICH_SERVICE)
    create_order(order["customer_id"], service["id"])
    create_order(globex["id"], rich["id"])

    body = get("/reports/sales-by-customer")

    assert body == [
        {
            "customer_id": globex["id"],
            "customer_name": "Globex Corporation",
            "order_count": 1,
            "total": "12000.00",
        },
        {
            "customer_id": order["customer_id"],
            "customer_name": "ACME Corp",
            "order_count": 2,
            "total": "3000.00",
        },
    ]


def test_sales_by_customer_includes_a_customer_without_sales(create_customer, order, get):
    idle = create_customer("Soylent Foods", "orders@soylentfoods.com")

    body = get("/reports/sales-by-customer")

    assert body[0]["order_count"] == 1
    assert body[1] == {
        "customer_id": idle["id"],
        "customer_name": "Soylent Foods",
        "order_count": 0,
        "total": "0.00",
    }


def test_sales_by_customer_is_ordered_by_total_desc(
    create_customer, create_service, create_order, order, service, get
):
    globex = create_customer("Globex Corporation", "billing@globex.com")
    initech = create_customer("Initech", "accounts@initech.com")
    rich = create_service(**RICH_SERVICE)
    create_order(globex["id"], rich["id"])
    create_order(order["customer_id"], service["id"])
    create_order(initech["id"], service["id"])

    totals = [row["total"] for row in get("/reports/sales-by-customer")]

    assert totals == ["12000.00", "3000.00", "1500.00"]


def test_sales_by_customer_keeps_a_customer_whose_only_order_was_cancelled(order, client, get):
    before = get("/reports/sales-by-customer")[0]

    client.post(f"/orders/{order['id']}/cancel")

    after = get("/reports/sales-by-customer")[0]

    assert (before["order_count"], before["total"]) == (1, "1500.00")
    assert after == {
        "customer_id": order["customer_id"],
        "customer_name": "ACME Corp",
        "order_count": 0,
        "total": "0.00",
    }


def test_report_money_is_a_json_string_and_the_count_an_integer(order, get):
    sale = get("/reports/last-sales")[0]
    customer_row = get("/reports/sales-by-customer")[0]

    assert isinstance(sale["amount"], str)
    assert isinstance(customer_row["total"], str)
    assert isinstance(customer_row["order_count"], int)


def test_reports_use_the_snapshot_not_the_current_service_price(order, service, client, get):
    client.patch(f"/services/{service['id']}", json={"suggested_price": "9999.00"})

    assert get("/reports/last-sales")[0]["amount"] == "1500.00"
    assert get("/reports/sales-by-customer")[0]["total"] == "1500.00"
