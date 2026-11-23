# softtek_code_assessment

Softtek Code Assessment

## Dependencies

The environment is managed with [uv](https://docs.astral.sh/uv/). `pyproject.toml` declares the
version ranges, `uv.lock` pins the exact versions and hashes, and `.python-version` pins
Python 3.12 — so `uv sync` recreates an identical virtualenv on any machine.

```bash
uv sync
```

`requirements.txt` is **generated** from `uv.lock`, never edited by hand. It exists so the project
can also be installed with plain `pip` (`pip install --require-hashes -r requirements.txt`) when
`uv` is not available.

Regenerate it after changing any dependency:

```bash
uv export --format requirements-txt --output-file requirements.txt
```

## Run it

```bash
createdb softtek_assessment
createdb softtek_assessment_test   # the test suite drops and recreates this one
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Without `uv`, using the pinned `requirements.txt` instead:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install --require-hashes -r requirements.txt
createdb softtek_assessment && createdb softtek_assessment_test
alembic upgrade head
```

## Sample data

After migrating, fill the database with sample customers:

```bash
uv run python -m app.seed
```

It is idempotent: if the table already has rows it does nothing, so running it on every boot
is harmless. To start from an empty database again:

```bash
psql -d softtek_assessment -c "TRUNCATE customers RESTART IDENTITY CASCADE"
```

Seeding is a manual step on purpose. Hooking it to the application's startup looks convenient,
but an app that writes rows just because it booted is a surprise in production and a race
between replicas; an explicit command is repeatable and easy to audit.

## Endpoints

Interactive documentation is served at `/docs` while the app is running.

### Customers

#### `POST /customers`

Registers a customer. The email must be unique.

```bash
curl -s -X POST localhost:8000/customers \
  -H 'content-type: application/json' \
  -d '{"name": "ACME Corp", "email": "contact@acme.com"}'
```

`201 Created`

```json
{ "id": 1, "name": "ACME Corp", "email": "contact@acme.com" }
```

| Status | When |
|---|---|
| `409 Conflict` | another customer already uses that email: `{"detail": "A customer with email contact@acme.com already exists"}` |
| `422 Unprocessable Entity` | a field is missing or invalid, e.g. an email without `@` |

The duplicate check exists twice on purpose: the `409` comes from an explicit check in the
crud layer so the client gets a readable message, while the unique index on `customers.email`
is what actually guarantees it — two concurrent requests cannot both insert the same email.

#### `GET /customers/{customer_id}`

Returns a single customer by id. `{customer_id}` is a path template: an actual request
looks like `/customers/1`.

```bash
curl -s localhost:8000/customers/1
```

`200 OK`

```json
{ "id": 1, "name": "ACME Corp", "email": "contact@acme.com" }
```

`404 Not Found`

```json
{ "detail": "Customer 45 not found" }
```
