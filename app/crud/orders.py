from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.crud import customers, services
from app.crud.common import get_or_404, save
from app.errors import ConflictError
from app.models import Order
from app.schemas import OrderCreate


def get(session: Session, order_id: int) -> Order:
    return get_or_404(session, Order, order_id, "Order")


def _next_folio(session: Session) -> str:
    """Take the next value from the sequence and pad it to six digits: 1000 -> "001000".

    The sequence is the source of truth, not a COUNT(*) + 1: two concurrent requests must
    never be able to compute the same folio.
    """
    value = session.execute(text("SELECT nextval('order_folio_seq')")).scalar_one()
    return f"{value:06d}"


def create(session: Session, payload: OrderCreate) -> Order:
    # Reuses the customer and service lookups, so a missing id produces the same
    # "Customer X not found" message here as it does in the rest of the API.
    customer = customers.get(session, payload.customer_id)
    service = services.get(session, payload.service_id)

    # Snapshot happens here by using the same data at created time but duplicating
    # the information.
    order = Order(
        folio=_next_folio(session),
        customer_id=customer.id,
        service_id=service.id,
        # The snapshot: copied by value, so editing the service later cannot rewrite
        # an order that was already placed.
        service_description=service.description,
        amount=service.suggested_price,
    )
    return save(session, order)


def cancel(session: Session, order_id: int) -> Order:
    order = get(session, order_id)
    if order.cancelled_at is not None:
        raise ConflictError(f"Order {order_id} is already cancelled")

    # now() comes from the database, the same clock that stamped created_at.
    order.cancelled_at = func.now()
    return save(session, order)
