from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import seed as seed_module
from app.models import Customer, Order, Service
from app.seed import CUSTOMERS, ORDERS, SERVICES, seed


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_seed_inserts_the_sample_data(session):
    created = seed(session)

    assert created == (len(CUSTOMERS), len(SERVICES), len(ORDERS))
    assert _count(session, Customer) == len(CUSTOMERS)
    assert _count(session, Service) == len(SERVICES)
    assert _count(session, Order) == len(ORDERS)


def test_seed_is_idempotent(session):
    seed(session)

    assert seed(session) == (0, 0, 0)
    assert _count(session, Customer) == len(CUSTOMERS)
    assert _count(session, Service) == len(SERVICES)
    assert _count(session, Order) == len(ORDERS)


def test_seed_skips_a_table_that_already_has_rows(session):
    """A hand-made row must survive, and orders are skipped when their services are missing."""
    session.add(Service(name="Hand made", description="d", suggested_price=Decimal("10.00")))
    session.commit()

    assert seed(session) == (len(CUSTOMERS), 0, 0)
    assert _count(session, Service) == 1
    assert _count(session, Customer) == len(CUSTOMERS)
    assert _count(session, Order) == 0


def test_seed_produces_the_shape_the_reports_need(session):
    """One cancelled order, and two customers with no sales at all."""
    seed(session)

    cancelled = session.scalar(
        select(func.count()).select_from(Order).where(Order.cancelled_at.is_not(None))
    )
    customers_with_sales = session.scalar(select(func.count(func.distinct(Order.customer_id))))

    assert cancelled == 1
    assert customers_with_sales == 6


def test_main_reports_what_it_did(session, monkeypatch, capsys):
    """Covers the CLI entry point without touching the development database."""
    factory = sessionmaker(
        bind=session.connection(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    monkeypatch.setattr(seed_module, "SessionLocal", factory)

    seed_module.main()
    assert capsys.readouterr().out.strip() == "Seeded 8 customers, 6 services and 20 orders."

    seed_module.main()
    assert (
        capsys.readouterr().out.strip()
        == "Nothing to seed: customers, services and orders already exist."
    )
