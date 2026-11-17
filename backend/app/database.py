from collections.abc import Generator
from datetime import datetime, timezone

import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import STORAGE_DIR, settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _engine_kwargs() -> dict:
    if settings.is_sqlite:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return {"connect_args": {"check_same_thread": False}}
    kwargs: dict = {"pool_pre_ping": True, "pool_recycle": 300, "pool_size": 5, "max_overflow": 5}
    if settings.db_ssl:
        kwargs["connect_args"] = {"ssl": {"ca": certifi.where()}}
    return kwargs


engine = create_engine(settings.database_url, **_engine_kwargs())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
