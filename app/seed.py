"""Populate the database with sample data for local development.

Run it after applying migrations:

    uv run python -m app.seed

The data is deterministic on purpose: the author and whoever reviews the repository
see the same ids, names and amounts, so the examples in the README stay valid.
The function is idempotent — running it twice does not duplicate anything.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Customer, Service

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

SERVICES: list[dict[str, object]] = [
    {
        "name": "24/7 support",
        "description": "Phone and email support, 8 hour response time",
        "suggested_price": Decimal("1500.00"),
    },
    {
        "name": "On-site installation",
        "description": "Installation at the customer site within 48 hours",
        "suggested_price": Decimal("2500.00"),
    },
    {
        "name": "Annual maintenance",
        "description": "Preventive maintenance, four visits per year",
        "suggested_price": Decimal("8400.00"),
    },
    {
        "name": "Remote diagnostics",
        "description": "Remote diagnostics session, up to two hours",
        "suggested_price": Decimal("450.00"),
    },
    {
        "name": "Data migration",
        "description": "Migration of up to 50 GB, with a validation report",
        "suggested_price": Decimal("3200.00"),
    },
    {
        "name": "Custom integration",
        "description": "Integration with a third party system, quoted per project",
        "suggested_price": Decimal("12000.00"),
    },
]


def _is_empty(session: Session, model: type[Customer] | type[Service]) -> bool:
    return session.scalar(select(model.id).limit(1)) is None


def seed(session: Session) -> tuple[int, int]:
    """Insert the sample rows, returning how many customers and services were created.

    Each table is checked separately, so a database with customers but without services
    gets the missing half instead of being skipped. Nothing is ever duplicated or
    overwritten: seeds must not clobber rows the developer created by hand.
    """
    customers_created = 0
    services_created = 0

    if _is_empty(session, Customer):
        session.add_all([Customer(**row) for row in CUSTOMERS])
        customers_created = len(CUSTOMERS)

    if _is_empty(session, Service):
        session.add_all([Service(**row) for row in SERVICES])
        services_created = len(SERVICES)

    if customers_created or services_created:
        session.commit()

    return customers_created, services_created


def main() -> None:
    with SessionLocal() as session:
        customers_created, services_created = seed(session)

    if customers_created or services_created:
        print(f"Seeded {customers_created} customers and {services_created} services.")
    else:
        print("Nothing to seed: customers and services already exist.")


if __name__ == "__main__":  # pragma: no cover - CLI guard, exercised by `python -m app.seed`
    main()
