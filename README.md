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

### Services

#### `POST /services`

Registers a service. `suggested_price` is the amount that orders copy when they are created.

```bash
curl -s -X POST localhost:8000/services \
  -H 'content-type: application/json' \
  -d '{"name": "24/7 support", "description": "Phone and email support, 8 hour response time", "suggested_price": "1500.00"}'
```

`201 Created`

```json
{
  "id": 1,
  "name": "24/7 support",
  "description": "Phone and email support, 8 hour response time",
  "suggested_price": "1500.00",
  "created_at": "2026-11-23T03:09:47.380435-06:00",
  "updated_at": "2026-11-23T03:09:47.380435-06:00"
}
```

`422 Unprocessable Entity` when `suggested_price` is zero, negative or carries more than two
decimals (`"1500.001"`), or when a field is missing or longer than its limit.

#### `GET /services/{service_id}`

Returns a single service. `{service_id}` is a path template: an actual request looks like
`/services/1`.

```bash
curl -s localhost:8000/services/1
```

`200 OK` — same body as the creation response.

`404 Not Found`

```json
{ "detail": "Service 9999 not found" }
```

#### `PATCH /services/{service_id}`

Changes only the fields present in the body; every other field keeps its current value. An empty
body `{}` is valid and changes nothing.

```bash
curl -s -X PATCH localhost:8000/services/1 \
  -H 'content-type: application/json' \
  -d '{"suggested_price": "1800.50"}'
```

`200 OK` — `suggested_price` is now `"1800.50"`, `name` and `description` are untouched, and
`updated_at` moved forward.

`404 Not Found` for an unknown id, `422 Unprocessable Entity` for an invalid price.

## Order folio

Every order gets a folio when it is created: six digits, zero padded — `"001000"`.

### Where it comes from

The migration creates a sequence next to the table:

```python
op.execute("CREATE SEQUENCE order_folio_seq START WITH 1000")
```

At insert time the application asks the database for the next value and pads it:

```python
def _next_folio(session: Session) -> str:
    value = session.execute(text("SELECT nextval('order_folio_seq')")).scalar_one()
    return f"{value:06d}"
```

```
nextval -> 1000   folio -> "001000"
nextval -> 1001   folio -> "001001"
nextval -> 9999   folio -> "009999"
```

The column is `VARCHAR(10)` with a unique index, so the database rejects a duplicate even if the
application logic ever gets it wrong.

### Why not `COUNT(*) + 1`, and why not the row id

- **`COUNT(*) + 1`** reads the table and computes the number in the application. Two concurrent
  requests read the same count, produce the same folio, and one of them dies against the unique
  index — with luck. Under load it becomes a retry loop.
- **The row id** is unique for free, but it only exists after the `INSERT`, so the folio would need
  a second `UPDATE` on every order. It also tells the reader how many orders exist, cancelled ones
  included.

### The date is not inside the folio

`"001000"` carries no date. The creation date lives in `created_at` on the same row: a timestamp
with time zone that can be queried, indexed and formatted however the client needs. Encoding a date
into the folio freezes the format forever, and makes two orders from the same day indistinguishable
by their identifier.

### Gaps are expected

```
nextval -> 1400   (the transaction then rolled back)
nextval -> 1401
```

A sequence is not transactional, so a value consumed by a transaction that later rolled back is
lost. That is correct: the folio identifies an order, not a count. Reusing numbers to "fix" the gaps
is how two orders end up sharing a folio.

## Notes

### Money is `NUMERIC`, never `float`

`suggested_price` is `NUMERIC(12, 2)` in PostgreSQL and `Decimal` in Python. Binary floats cannot
hold most decimal fractions exactly — `1500.10` is stored as `1500.09999999999990905…` — and those
errors compound once amounts are added together. The column keeps the exact value, and
`max_digits=12, decimal_places=2` in the schema rejects `1.234` at the edge instead of letting
Postgres round it silently (`SELECT 1.234::numeric(12,2)` returns `1.23`).

`Decimal` is serialized as a JSON **string** (`"1500.00"`), so it never becomes a float on the way
in or out.

### `now()` is the transaction timestamp, and that shapes the tests

PostgreSQL's `now()` returns the moment the **transaction** started, not the moment of the
statement. Every `created_at` / `updated_at` written inside one transaction gets the same value.

In production each request is its own transaction, so the difference shows:

```
insert      created_at=02:55:30.478248  updated_at=02:55:30.478248
patch +1.5s created_at=02:55:30.478248  updated_at=02:55:31.989281
```

The test suite wraps each test in a single outer transaction, so the same 1.5 second gap
disappears:

```
insert      created_at=02:55:19.141075  updated_at=02:55:19.141075
patch +1.5s created_at=02:55:19.141075  updated_at=02:55:19.141075   ← frozen
```

Two consequences:

- **Tests never assert on timestamps.** A test claiming `updated_at > created_at` would fail in
  the suite while passing in production — a test lying about the system.
- **Reports sort by `(created_at DESC, id DESC)`.** Ordering by `created_at` alone is ambiguous for
  rows written in the same transaction; the id is the tie-breaker that makes "last 10 sales"
  deterministic.

### Alembic does not see sequences, so migrations must drop them

`order_folio_seq` is created with raw SQL, because autogenerate only compares tables, columns and
indexes:

```python
op.execute("CREATE SEQUENCE order_folio_seq START WITH 1000")
```

The mirror image is the part that gets forgotten — `downgrade` has to drop it by hand as well:

```python
def downgrade() -> None:
    op.drop_table("orders")
    op.execute("DROP SEQUENCE order_folio_seq")
```

Without that line, `downgrade` followed by `upgrade` fails with
`ERROR: relation "order_folio_seq" already exists`. It is a migration that only breaks on someone
else's machine, months later, in the one path the test suite never walks: the fixtures always
start from a dropped schema and only ever run `upgrade`.

### `extra="ignore"` on `OrderCreate` is load bearing

An order payload is `{customer_id, service_id}` and nothing else. The amount is not a field of the
request: the server reads it from the service. Pydantic ignores unknown keys by default, so a client
sending `{"customer_id": 1, "service_id": 2, "amount": "1.00"}` gets a `201` whose body says
`"amount": "1500.00"` — the attempt is dropped, not honoured.

The setting is written out even though it is the default, so it does not get "hardened" later into
`extra="forbid"`. Forbidding would turn that request into a `422`, break
`test_client_cannot_set_the_amount`, and tell clients the amount is a field they are allowed to
set — the opposite of the rule.

### `nextval()` is atomic, and that is the whole point

`nextval()` is a single atomic operation inside the database. Concurrent sessions cannot receive the
same value, and no application lock or `SELECT ... FOR UPDATE` is involved. Measured on this schema
with 8 threads taking 50 values each:

```
400 values, 400 unique, min=1000 max=1399
```

The same workload built on `COUNT(*) + 1` would produce duplicates: the read and the insert are two
separate statements, and everything that happens between them is a window where another request can
read the same count. The sequence closes that window by being the counter itself, which is why the
folio is generated there and not in Python.

### `COUNT(o.id)`, not `COUNT(*)`, when the join is optional

The sales-by-customer report must list customers with no sales at all, so the query joins the other
way round:

```sql
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.cancelled_at IS NULL
```

With an outer join, `COUNT(*)` counts the empty row the join invents for a customer without orders
and reports one sale. `COUNT(o.id)` counts real rows only:

| expression | customer with 3 sales | customer with none |
|---|---|---|
| `COUNT(*)` | 3 | **1** ← wrong |
| `COUNT(o.id)` | 3 | 0 |

Measured against the same pair of tables:

```
A|3|3|17.5      ← 3 sales, COUNT(*)=3, COUNT(col)=3, total 17.50
B|1|0|0         ← no sales, COUNT(*)=1, COUNT(col)=0, total 0
```

### `SUM` over no rows is `NULL`, so the total needs `COALESCE`

`SUM` of zero rows returns `NULL`, not `0`, and a report answering `"total": null` pushes the
problem onto every client:

```
SUM(x) IS NULL -> true     COALESCE(SUM(x), 0) -> 0
```

`COALESCE(SUM(o.amount), 0)` is what keeps a customer with no sales in the report instead of
returning `NULL`. But the literal `0` is an integer, and the resulting `Decimal("0")` serializes as
`"0"`, not `"0.00"` — the scale is part of the contract, so the total is cast:

```sql
CAST(COALESCE(SUM(o.amount), 0) AS numeric(12,2))
```

```
without the cast -> 0        with the cast -> 0.00
```

### Why each row of the last 10 sales carries its id and folio

The requirements ask for four fields: customer, service description, amount and creation date. Each
row also carries the order `id` and `folio`. They cost nothing and make the report actionable:
`GET /orders/{id}` resolves any row without a second search, and the folio is what a person quotes
on the phone. A report you cannot act on is a report someone has to re-query by hand.

### `select_from(Customer)` is insurance, not a requirement

The report is built with `.select_from(Customer)` in front of the join. Both versions compile to the
same statement and return the same eight rows:

```
customers LEFT OUTER JOIN orders ON orders.customer_id = customers.id
  AND orders.cancelled_at IS NULL
```

It stays because it pins the `FROM` to the entity the report is about. Without it, SQLAlchemy infers
the `FROM` from whichever entity appears first in the select list — so an edit that drops
`Customer.id` from the columns could turn the query inside out and still produce plausible numbers.

### The cancelled filter belongs in the `ON` clause, not the `WHERE`

Both placements return the same rows today:

```
ON    -> Globex, ACME, Northwind, Wayne, Initech, Stark, Umbrella, Soylent
WHERE -> Globex, ACME, Northwind, Wayne, Initech, Stark, Umbrella, Soylent
```

That agreement is an accident of this particular predicate. An unmatched row has `NULL` in every
order column, and `NULL IS NULL` is true, so the outer row survives a `WHERE cancelled_at IS NULL`
— which is exactly what lets the wrong version pass code review.

Add one predicate that is not NULL-safe and the difference shows up:

```
WHERE cancelled_at IS NULL AND amount > 5000 -> 4 customers
ON    cancelled_at IS NULL AND amount > 5000 -> 8 customers
```

In the `WHERE` version a customer whose orders all fail `amount > 5000` had rows matched by the
join, then filtered out, and with no surviving row it vanishes from the report — zeroes included.
