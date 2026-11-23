from fastapi import APIRouter

from app.crud import reports as crud
from app.deps import SessionDep
from app.schemas import LastSaleRead, SalesByCustomerRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/last-sales", response_model=list[LastSaleRead])
def last_sales(session: SessionDep):
    return crud.last_sales(session)


@router.get("/sales-by-customer", response_model=list[SalesByCustomerRead])
def sales_by_customer(session: SessionDep):
    return crud.sales_by_customer(session)
