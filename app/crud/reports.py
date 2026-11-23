from collections.abc import Sequence

from sqlalchemy import Numeric, cast, desc, func, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.models import Customer, Order

LAST_SALES_LIMIT = 10


def last_sales(session: Session, limit: int = LAST_SALES_LIMIT) -> Sequence[Row]:
    """The most recent sales, newest first, cancelled orders excluded.

    The id is part of the ordering on purpose: created_at alone is not unique — every row
    written inside one transaction shares the same now() — so without the tie-breaker the
    result of "the last 10" would be whatever the planner felt like returning.
    """
    statement = (
        select(
            Order.id,
            Order.folio,
            Customer.name.label("customer_name"),
            Order.service_description,
            Order.amount,
            Order.created_at,
        )
        .join(Customer, Customer.id == Order.customer_id)
        .where(Order.cancelled_at.is_(None))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
    )
    return session.execute(statement).all()


def sales_by_customer(session: Session) -> Sequence[Row]:
    """Order count and accumulated amount per customer, biggest spender first.

    The join is a LEFT JOIN so a customer with no sales still appears, and the cancelled
    filter sits in the ON clause: in the WHERE it would silently drop those customers.
    """
    statement = (
        select(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            # COUNT(o.id), not COUNT(*): on an outer join, COUNT(*) counts the empty row
            # the join invents for a customer without orders and reports one sale.
            func.count(Order.id).label("order_count"),
            # SUM of no rows is NULL, and the cast keeps the scale ("0.00", not "0").
            cast(func.coalesce(func.sum(Order.amount), 0), Numeric(12, 2)).label("total"),
        )
        .select_from(Customer)
        .outerjoin(
            Order,
            (Order.customer_id == Customer.id) & Order.cancelled_at.is_(None),
        )
        .group_by(Customer.id, Customer.name)
        .order_by(desc("total"), Customer.id)
    )
    return session.execute(statement).all()
