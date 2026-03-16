from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient


# ------------------------------------------------------------------
# Force a dedicated SQLite database for tests BEFORE importing app.*
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_TMPDIR = Path(tempfile.mkdtemp(prefix="student_center_tests_"))
TEST_DB_PATH = TEST_TMPDIR / "test_app.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SEED_DB_ON_STARTUP"] = "0"
os.environ["COOKIE_SECURE"] = "0"
os.environ["ENV"] = "test"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    Holiday,
    Payment,
    Service,
    Student,
    StudentService,
    User,
)
from app.routers.auth import FAILED_LOGINS  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db() -> Iterator[None]:
    """Fresh database for every test."""
    FAILED_LOGINS.clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    FAILED_LOGINS.clear()


@pytest.fixture()
def db_session() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_user(db_session):
    user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        role="admin",
        is_active=1,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def demo_user(db_session):
    user = User(
        username="demo",
        password_hash=hash_password("demo123"),
        role="demo",
        is_active=1,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_client(client: TestClient, admin_user: User) -> TestClient:
    token = create_access_token(subject=admin_user.username, role=admin_user.role)
    client.cookies.set("access_token", token)
    return client


@pytest.fixture()
def seeded_services(db_session):
    services = [
        Service(name="Speech Therapy"),
        Service(name="Occupational Therapy"),
        Service(name="Psychology"),
    ]
    db_session.add_all(services)
    db_session.commit()
    for svc in services:
        db_session.refresh(svc)
    return services


@pytest.fixture()
def seeded_student(db_session, seeded_services):
    student = Student(
        amka="12345678901",
        center="Giannitsa",
        first_name="Maria",
        last_name="Papadopoulou",
        date_of_birth=date(2015, 5, 20),
        parent_name="Eleni Papadopoulou",
        parent_phone="6900000000",
        assessment_expiry_date=date(2026, 12, 31),
        admin_comment="Initial note",
    )
    db_session.add(student)
    db_session.commit()

    link1 = StudentService(
        student_amka=student.amka,
        service_id=seeded_services[0].id,
        total_sessions=4,
    )
    link2 = StudentService(
        student_amka=student.amka,
        service_id=seeded_services[1].id,
        total_sessions=2,
    )
    db_session.add_all([link1, link2])
    db_session.commit()
    return student


def create_appointment(
    db_session,
    *,
    student_amka: str,
    service_id: int,
    center: str = "Giannitsa",
    day: date = date(2026, 3, 16),
    start_time_value: time = time(10, 0),
    duration_min: int = 45,
    status: str = "scheduled",
    created_at: datetime | None = None,
):
    ap = Appointment(
        student_amka=student_amka,
        service_id=service_id,
        center=center,
        day=day,
        start_time=start_time_value,
        duration_min=duration_min,
        status=status,
    )
    if created_at is not None:
        ap.created_at = created_at
    db_session.add(ap)
    db_session.commit()
    db_session.refresh(ap)
    return ap


@pytest.fixture()
def helper_create_appointment():
    return create_appointment


@pytest.fixture()
def payment_factory(db_session):
    def _make(student_amka: str, amount_cents: int = 2500, payment_date: date = date(2026, 3, 1), comment: str | None = None):
        p = Payment(
            student_amka=student_amka,
            amount_cents=amount_cents,
            payment_date=payment_date,
            comment=comment,
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        return p

    return _make


@pytest.fixture()
def holiday_factory(db_session):
    def _make(center: str, day: date, note: str | None = None):
        h = Holiday(center=center, day=day, note=note)
        db_session.add(h)
        db_session.commit()
        db_session.refresh(h)
        return h

    return _make
