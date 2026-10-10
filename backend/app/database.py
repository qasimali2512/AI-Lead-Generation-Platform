from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Supabase's pooler drops idle connections, so recycle them early.
    pool_recycle=300,
    connect_args={
        # Supabase pooler (port 6543) runs in transaction mode, which
        # does not support psycopg3 server-side prepared statements.
        "prepare_threshold": None,
        # TCP keepalives stop idle connections from being dropped
        # silently while a slow AI call is running.
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session to FastAPI routes."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()