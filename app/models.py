# app/models.py
from __future__ import annotations

from datetime import datetime, date, time

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Time,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# -------------------------
# User
# -------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # admin / demo (ή οτιδήποτε άλλο)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="admin")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# -------------------------
# Student
# -------------------------
class Student(Base):
    __tablename__ = "students"

    # AMKA = primary key
    amka: Mapped[str] = mapped_column(String(20), primary_key=True)

    # κέντρο εγγραφής μαθητή
    center: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Giannitsa",  # Giannitsa / KryaVrisi
    )

    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    parent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parent_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    assessment_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    admin_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    services: Mapped[list["StudentService"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"


# -------------------------
# Service
# -------------------------
class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    student_links: Mapped[list["StudentService"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
    )


# -------------------------
# StudentService (sessions per service)
# -------------------------
class StudentService(Base):
    __tablename__ = "student_services"
    __table_args__ = (
        UniqueConstraint("student_amka", "service_id", name="uq_student_service"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    student_amka: Mapped[str] = mapped_column(
        ForeignKey("students.amka", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )

    # συνολικός αριθμός συνεδριών που έχει το πακέτο/συμφωνία του μαθητή για την υπηρεσία
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    student: Mapped["Student"] = relationship(back_populates="services")
    service: Mapped["Service"] = relationship(back_populates="student_links")


# -------------------------
# Appointment (scheduled sessions)
# -------------------------
class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    student_amka: Mapped[str] = mapped_column(
        ForeignKey("students.amka", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )

    # κέντρο στο οποίο γίνεται η συνεδρία (συνήθως ίδιο με του μαθητή,
    # αλλά το κρατάμε μέσα στο appointment για ευκολότερο φιλτράρισμα/αναφορές)
    center: Mapped[str] = mapped_column(String(20), nullable=False)

    # ημερομηνία + ώρα (όχι start_at datetime)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)

    # προαιρετική διάρκεια (λεπτά)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # scheduled / completed / canceled
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")


# -------------------------
# Payment (monthly payments per student)
# -------------------------
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_amka: Mapped[str] = mapped_column(
        ForeignKey("students.amka", ondelete="CASCADE"), nullable=False
    )

    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ποσό σε cents (πχ 25.00€ => 2500)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="payments")


# -------------------------
# Holidays (per center)
# -------------------------
class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("center", "day", name="uq_holiday_center_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Giannitsa / KryaVrisi
    center: Mapped[str] = mapped_column(String(20), nullable=False)

    day: Mapped[date] = mapped_column(Date, nullable=False)

    note: Mapped[str | None] = mapped_column(String(120), nullable=True)
