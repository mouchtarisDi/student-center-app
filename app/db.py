import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_database_url(url: str) -> str:

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Αν δεν έχεις DATABASE_URL, δουλεύει τοπικά με SQLite
_raw_url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
DATABASE_URL = _normalize_database_url(_raw_url)

DB_SCHEMA = os.getenv("DB_SCHEMA", "").strip()  # "prod" ή "demo" (ή κενό)

# SQLite χρειάζεται special connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Postgres: βάλε search_path ώστε ΟΛΑ τα queries/DDL να “βλέπουν” το σωστό schema
if (not DATABASE_URL.startswith("sqlite")) and DB_SCHEMA:
    connect_args = {"options": f"-csearch_path={DB_SCHEMA}"}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()