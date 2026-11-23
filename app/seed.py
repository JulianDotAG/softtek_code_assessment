"""Populate the database with sample data for local development.

Run it after applying migrations:

    uv run python -m app.seed

The data is deterministic on purpose: the author and whoever reviews the repository
see the same ids, names and amounts, so the examples in the README stay valid.
The function is idempotent — running it twice does not duplicate anything.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Customer

CUSTOMERS: list[dict[str, str]] = [
    {"name": "ACME Corp", "email": "contact@acme.com"},
    {"name": "Northwind Traders", "email": "purchases@northwind.com"},
    {"name": "Globex Corporation", "email": "billing@globex.com"},
    {"name": "Initech", "email": "accounts@initech.com"},
    {"name": "Umbrella Logistics", "email": "ops@umbrella-logistics.com"},
    {"name": "Stark Industries", "email": "procurement@stark.com"},
    {"name": "Wayne Enterprises", "email": "finance@wayne.com"},
    {"name": "Soylent Foods", "email": "orders@soylentfoods.com"},
]


def seed(session: Session) -> int:
    """Insert the sample customers, returning how many were created.

    Returns 0 when the table already has data: seeding must never duplicate rows, and
    it must never overwrite whatever the developer created by hand.
    """
    if session.scalar(select(Customer.id).limit(1)) is not None:
        return 0

    customers = [Customer(**row) for row in CUSTOMERS]
    session.add_all(customers)
    session.commit()
    return len(customers)


def main() -> None:
    with SessionLocal() as session:
        created = seed(session)

    if created:
        print(f"Seeded {created} customers.")
    else:
        print("Customers already exist; nothing seeded.")


if __name__ == "__main__":
    main()
