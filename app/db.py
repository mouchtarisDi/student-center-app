import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_database_url(url: str) -> str:
    # """
    # Κάποιοι providers (π.χ. Render/Heroku) μπορεί να δώσουν DATABASE_URL που ξεκινά με:
    # postgres://

    # Η SQLAlchemy θέλει:
    # postgresql://

    # Αν δεν το κάνεις normalize, η εφαρμογή μπορεί να “σκάσει” στο startup σε production.
    # """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Αν δεν έχεις DATABASE_URL, δουλεύει τοπικά με SQLite
_raw_url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
DATABASE_URL = _normalize_database_url(_raw_url)

# SQLite χρειάζεται special connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

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