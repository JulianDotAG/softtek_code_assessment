from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Service
from app.schemas import ServiceCreate, ServiceUpdate


def get(session: Session, service_id: int) -> Service:
    service = session.get(Service, service_id)
    if service is None:
        raise NotFoundError("Service", service_id)
    return service


def create(session: Session, payload: ServiceCreate) -> Service:
    service = Service(**payload.model_dump())
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


def update(session: Session, service_id: int, payload: ServiceUpdate) -> Service:
    service = get(session, service_id)

    # exclude_unset is what makes PATCH safe: fields the client did not send are absent
    # from the dict, so they are never overwritten with None.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    session.commit()
    session.refresh(service)
    return service
