"""Small helpers shared by the crud modules.

They exist because the three resources do the same two things over and over: fetch a row
by primary key or fail with the API's own 404, and commit an object so the values the
database generates (id, timestamps) are loaded before the response is serialized.
"""

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Base


def get_or_404[ModelT: Base](
    session: Session, model: type[ModelT], identifier: int, resource: str
) -> ModelT:
    """Return the row with this primary key, raising `NotFoundError` when there is none."""
    instance = session.get(model, identifier)
    if instance is None:
        raise NotFoundError(resource, identifier)
    return instance


def save[ModelT: Base](session: Session, instance: ModelT) -> ModelT:
    """Insert or update the object, then reload it so server-generated values are present."""
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance
