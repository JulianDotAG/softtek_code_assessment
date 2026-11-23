from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Customer
from app.schemas import CustomerCreate


def get(session: Session, customer_id: int) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer", customer_id)
    return customer


def create(session: Session, payload: CustomerCreate) -> Customer:
    # Explicit check so a duplicate returns 409 instead of surfacing a raw IntegrityError
    # as a 500. The unique index on customers.email remains the real guarantee.
    existing = session.scalar(select(Customer).where(Customer.email == payload.email))
    if existing is not None:
        raise ConflictError(f"A customer with email {payload.email} already exists")

    customer = Customer(**payload.model_dump())
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer
