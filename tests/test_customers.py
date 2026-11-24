"""`POST /customers` and `GET /customers/{customer_id}`.

The email is the identity of a customer: it is unique (409 on a repeat, whatever the name)
and validated (422). A name is required and at most 200 characters. An unknown id is a
404 whose message names the resource and the id.
"""


def test_create_customer_returns_the_stored_customer(client):
    response = client.post("/customers", json={"name": "ACME Corp", "email": "contact@acme.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "ACME Corp"
    assert body["email"] == "contact@acme.com"


def test_created_customer_can_be_fetched_by_id(create_customer, get):
    created = create_customer()

    assert get(f"/customers/{created['id']}") == created


def test_duplicate_email_returns_409_even_with_another_name(create_customer, client):
    create_customer()

    response = client.post("/customers", json={"name": "Other Co", "email": "contact@acme.com"})

    assert response.status_code == 409
    assert response.json()["detail"] == "A customer with email contact@acme.com already exists"


def test_email_is_stored_lowercased(client):
    """`EmailStr` normalises the domain only; the API normalises the rest of the address."""
    response = client.post("/customers", json={"name": "ACME Corp", "email": "Contact@ACME.com"})

    assert response.status_code == 201
    assert response.json()["email"] == "contact@acme.com"


def test_duplicate_email_ignoring_case_returns_409(create_customer, client):
    create_customer()

    response = client.post("/customers", json={"name": "Other Co", "email": "CONTACT@ACME.COM"})

    assert response.status_code == 409
    assert response.json()["detail"] == "A customer with email contact@acme.com already exists"


def test_missing_name_returns_422(client):
    response = client.post("/customers", json={"email": "contact@acme.com"})

    assert response.status_code == 422


def test_empty_name_returns_422(client):
    response = client.post("/customers", json={"name": "", "email": "contact@acme.com"})

    assert response.status_code == 422


def test_name_over_200_characters_returns_422(client):
    response = client.post("/customers", json={"name": "x" * 201, "email": "contact@acme.com"})

    assert response.status_code == 422


def test_malformed_email_returns_422(client):
    response = client.post("/customers", json={"name": "ACME Corp", "email": "not-an-email"})

    assert response.status_code == 422


def test_missing_customer_returns_404(client):
    response = client.get("/customers/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer 9999 not found"}


def test_customer_id_must_be_an_integer(client):
    response = client.get("/customers/abc")

    assert response.status_code == 422
