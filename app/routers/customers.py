from fastapi import APIRouter, status

from app.crud import customers as crud
from app.deps import SessionDep
from app.schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, session: SessionDep):
    return crud.create(session, payload)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: SessionDep):
    return crud.get(session, customer_id)
