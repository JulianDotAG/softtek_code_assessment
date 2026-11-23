from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import seed as seed_module
from app.models import Customer
from app.seed import CUSTOMERS, seed


def _customer_count(session) -> int:
    return session.scalar(select(func.count()).select_from(Customer))


def test_seed_inserts_the_sample_customers(session):
    created = seed(session)

    assert created == len(CUSTOMERS)
    assert _customer_count(session) == len(CUSTOMERS)


def test_seed_is_idempotent(session):
    seed(session)

    assert seed(session) == 0
    assert _customer_count(session) == len(CUSTOMERS)


def test_main_reports_what_it_did(session, monkeypatch, capsys):
    """Covers the CLI entry point without touching the development database."""
    factory = sessionmaker(
        bind=session.connection(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    monkeypatch.setattr(seed_module, "SessionLocal", factory)

    seed_module.main()
    assert capsys.readouterr().out.strip() == "Seeded 8 customers."

    seed_module.main()
    assert capsys.readouterr().out.strip() == "Customers already exist; nothing seeded."
