"""Database setup and session management."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

_DEFAULT_DB = Path(__file__).parent.parent / "aegis.db"


def _db_url() -> str:
    path = os.environ.get("AEGIS_DB_PATH", str(_DEFAULT_DB))
    return f"sqlite:///{path}"


engine = create_engine(_db_url(), echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
