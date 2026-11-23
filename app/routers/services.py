from fastapi import APIRouter, status

from app.crud import services as crud
from app.deps import SessionDep
from app.schemas import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, session: SessionDep):
    return crud.create(session, payload)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, session: SessionDep):
    return crud.get(session, service_id)


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(service_id: int, payload: ServiceUpdate, session: SessionDep):
    return crud.update(session, service_id, payload)
