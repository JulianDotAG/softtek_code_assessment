from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.common import get_or_404, save
from app.errors import ConflictError
from app.models import Customer
from app.schemas import CustomerCreate


def get(session: Session, customer_id: int) -> Customer:
    return get_or_404(session, Customer, customer_id, "Customer")


def create(session: Session, payload: CustomerCreate) -> Customer:
    # Explicit check so a duplicate returns 409 instead of surfacing a raw IntegrityError
    # as a 500. The unique index on customers.email remains the real guarantee.
    existing = session.scalar(select(Customer).where(Customer.email == payload.email))
    if existing is not None:
        raise ConflictError(f"A customer with email {payload.email} already exists")

    return save(session, Customer(**payload.model_dump()))
