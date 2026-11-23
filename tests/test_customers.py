CUSTOMER = {"name": "ACME Corp", "email": "contact@acme.com"}


def test_create_customer_returns_201_with_payload(client):
    response = client.post("/customers", json=CUSTOMER)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "ACME Corp"
    assert body["email"] == "contact@acme.com"


def test_created_customer_is_persisted(client):
    created_response = client.post("/customers", json=CUSTOMER)
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()

    fetched = client.get(f"/customers/{created['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created


def test_create_customer_with_duplicate_email_returns_409(client):
    assert client.post("/customers", json=CUSTOMER).status_code == 201

    response = client.post("/customers", json={**CUSTOMER, "name": "Other Co"})

    assert response.status_code == 409
    assert "contact@acme.com" in response.json()["detail"]


def test_create_customer_with_invalid_email_returns_422(client):
    response = client.post("/customers", json={"name": "ACME", "email": "not-an-email"})

    assert response.status_code == 422


def test_create_customer_without_name_returns_422(client):
    response = client.post("/customers", json={"email": "contact@acme.com"})

    assert response.status_code == 422


def test_get_customer_by_id(client):
    created_response = client.post("/customers", json=CUSTOMER)
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()

    response = client.get(f"/customers/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["email"] == "contact@acme.com"


def test_get_missing_customer_returns_404(client):
    response = client.get("/customers/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer 9999 not found"
