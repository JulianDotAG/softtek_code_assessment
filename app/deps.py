from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_session

# Routers depend on this alias instead of `session: Session = Depends(get_session)`.
# A function call in a default argument trips ruff's B008, and Annotated is the form
# FastAPI documents today. One definition, four routers.
SessionDep = Annotated[Session, Depends(get_session)]
