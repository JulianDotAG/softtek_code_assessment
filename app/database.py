from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# The engine is created at import time but connects lazily: importing this module
# never touches the database, so the app can start (and fail cleanly) without one.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False keeps attribute values readable after commit(), which matters
# because routers return ORM objects straight to the response serializer.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One session per request, always closed.

    Used as a FastAPI dependency, so the generator's cleanup runs after the response
    is produced, even when the handler raises.
    """
    with SessionLocal() as session:
        yield session
