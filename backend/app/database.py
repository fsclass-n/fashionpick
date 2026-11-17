from collections.abc import Generator
from datetime import datetime, timezone

import certifi
from sqlalchemy import create_engine, inspect, text
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


def ensure_schema() -> None:
    """create_all 은 기존 테이블에 컬럼을 추가하지 않으므로, 신규 컬럼은 여기서 보강한다."""
    insp = inspect(engine)
    if "orders" in insp.get_table_names() and "user_id" not in {c["name"] for c in insp.get_columns("orders")}:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE orders ADD COLUMN user_id INTEGER NULL"))
            conn.execute(text("CREATE INDEX ix_orders_user_id ON orders (user_id)"))
