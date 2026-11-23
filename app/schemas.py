from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    # gt=0 lives in the schema, so the rule is enforced before the database sees it.
    suggested_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class ServiceUpdate(BaseModel):
    """Every field is optional: a PATCH only touches what it receives."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    suggested_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    suggested_price: Decimal
    created_at: datetime
    updated_at: datetime


class CustomerSummary(BaseModel):
    """The customer, trimmed to what an order needs to show."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class OrderCreate(BaseModel):
    # The amount is intentionally absent: it comes from the service, never from the client.
    # extra="ignore" is pydantic's default, spelled out because this rule is load bearing.
    model_config = ConfigDict(extra="ignore")

    customer_id: int
    service_id: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    customer_id: int
    service_id: int
    service_description: str
    amount: Decimal
    created_at: datetime
    cancelled_at: datetime | None
    customer: CustomerSummary


class LastSaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    customer_name: str
    service_description: str
    amount: Decimal
    created_at: datetime


class SalesByCustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    customer_name: str
    order_count: int
    total: Decimal
