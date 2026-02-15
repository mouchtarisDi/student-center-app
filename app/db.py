import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_database_url(url: str) -> str:
    """
    Render/Heroku καμιά φορά δίνουν DATABASE_URL που ξεκινά με postgres://
    Η SQLAlchemy θέλει postgresql://
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Αν δεν έχεις DATABASE_URL, δουλεύει τοπικά με SQLite
DATABASE_URL = _normalize_database_url(
    os.getenv("DATABASE_URL", "postgresql://student_center_db_user:ERwftoONNFlf6UU9zeb63M4QoaD9mP6x@dpg-d68th6bh46gs73fkhp8g-a/student_center_db")
)

# SQLite χρειάζεται special connect_args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
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
