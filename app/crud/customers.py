from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.common import get_or_404, save
from app.errors import ConflictError
from app.models import Customer
from app.schemas import CustomerCreate


def get(session: Session, customer_id: int) -> Customer:
    return get_or_404(session, Customer, customer_id, "Customer")


def create(session: Session, payload: CustomerCreate) -> Customer:
    """Store the email lowercased and treat it as the customer's identity.

    The address is normalised on the way in, so "Contact@ACME.com" and "contact@acme.com"
    are the same customer. The comparison uses lower(email) as well, to catch rows written
    before the normalisation existed.
    """
    email = payload.email.lower()

    # Explicit check so a duplicate returns 409 instead of surfacing a raw IntegrityError
    # as a 500. The unique index on customers.email remains the real guarantee.
    existing = session.scalar(select(Customer).where(func.lower(Customer.email) == email))
    if existing is not None:
        raise ConflictError(f"A customer with email {email} already exists")

    return save(session, Customer(name=payload.name, email=email))
