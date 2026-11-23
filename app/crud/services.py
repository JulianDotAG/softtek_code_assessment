from sqlalchemy.orm import Session

from app.crud.common import get_or_404, save
from app.models import Service
from app.schemas import ServiceCreate, ServiceUpdate


def get(session: Session, service_id: int) -> Service:
    return get_or_404(session, Service, service_id, "Service")


def create(session: Session, payload: ServiceCreate) -> Service:
    return save(session, Service(**payload.model_dump()))


def update(session: Session, service_id: int, payload: ServiceUpdate) -> Service:
    service = get(session, service_id)

    # exclude_unset is what makes PATCH safe: fields the client did not send are absent
    # from the dict, so they are never overwritten with None.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    return save(session, service)
