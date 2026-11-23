"""Populate the database with sample data for local development.

Run it after applying migrations:

    uv run python -m app.seed

The data is deterministic on purpose: the author and whoever reviews the repository
see the same ids, names and amounts, so the examples in the README stay valid. Only the
order timestamps move — they are placed relative to now so the reports show a plausible
history instead of twenty rows sharing one second. The function is idempotent: running it
twice does not duplicate anything.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import orders as orders_crud
from app.database import SessionLocal
from app.models import Customer, Order, Service
from app.schemas import OrderCreate

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

# (customer email, service name, hours ago, cancelled)
# Twenty orders so the "last 10 sales" limit is actually exercised, one cancelled so both
# reports have something to exclude, and two customers left without orders so the summary
# has to render zeroes.
ORDERS: list[tuple[str, str, int, bool]] = [
    ("contact@acme.com", "Custom integration", 0, False),
    ("billing@globex.com", "Annual maintenance", 4, False),
    ("contact@acme.com", "24/7 support", 8, False),
    ("purchases@northwind.com", "Data migration", 12, False),
    ("accounts@initech.com", "On-site installation", 18, False),
    ("contact@acme.com", "Remote diagnostics", 24, False),
    ("billing@globex.com", "Custom integration", 30, False),
    ("purchases@northwind.com", "Annual maintenance", 36, False),
    ("procurement@stark.com", "24/7 support", 42, False),
    ("contact@acme.com", "On-site installation", 48, False),
    ("accounts@initech.com", "Data migration", 54, False),
    ("billing@globex.com", "24/7 support", 60, False),
    ("purchases@northwind.com", "On-site installation", 66, False),
    ("finance@wayne.com", "Custom integration", 72, False),
    ("contact@acme.com", "Annual maintenance", 78, False),
    ("accounts@initech.com", "Remote diagnostics", 84, False),
    ("billing@globex.com", "Data migration", 90, False),
    ("purchases@northwind.com", "Remote diagnostics", 96, False),
    ("procurement@stark.com", "On-site installation", 102, False),
    ("finance@wayne.com", "24/7 support", 108, True),
]


def _is_empty(session: Session, model: type[Customer] | type[Service] | type[Order]) -> bool:
    return session.scalar(select(model.id).limit(1)) is None


def _seed_orders(session: Session) -> int:
    if not _is_empty(session, Order):
        return 0

    customers = {customer.email: customer for customer in session.scalars(select(Customer))}
    services = {service.name: service for service in session.scalars(select(Service))}
    # Orders are skipped unless every row they reference exists: a half seeded database
    # must leave the script quiet instead of raising a KeyError.
    if any(email not in customers or name not in services for email, name, _, _ in ORDERS):
        return 0

    now = datetime.now(UTC)
    for email, service_name, hours_ago, cancelled in ORDERS:
        order = orders_crud.create(
            session,
            OrderCreate(
                customer_id=customers[email].id,
                service_id=services[service_name].id,
            ),
        )
        # Placed in the past so "last 10 sales" has a visible order to show.
        order.created_at = now - timedelta(hours=hours_ago)
        if cancelled:
            order.cancelled_at = order.created_at + timedelta(hours=1)
        session.commit()

    return len(ORDERS)


def seed(session: Session) -> tuple[int, int, int]:
    """Insert the sample rows, returning how many customers, services and orders it created.

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

    orders_created = _seed_orders(session)
    return customers_created, services_created, orders_created


def main() -> None:
    with SessionLocal() as session:
        customers_created, services_created, orders_created = seed(session)

    if customers_created or services_created or orders_created:
        print(
            f"Seeded {customers_created} customers, {services_created} services "
            f"and {orders_created} orders."
        )
    else:
        print("Nothing to seed: customers, services and orders already exist.")


if __name__ == "__main__":  # pragma: no cover - CLI guard, exercised by `python -m app.seed`
    main()
