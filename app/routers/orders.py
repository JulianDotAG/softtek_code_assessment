from fastapi import APIRouter, status

from app.crud import orders as crud
from app.deps import SessionDep
from app.schemas import OrderCreate, OrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, session: SessionDep):
    return crud.create(session, payload)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, session: SessionDep):
    return crud.get(session, order_id)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(order_id: int, session: SessionDep):
    return crud.cancel(session, order_id)
