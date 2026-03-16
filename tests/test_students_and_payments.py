from __future__ import annotations

from datetime import date, time

import pytest

from app.models import Appointment, Payment, Student, StudentService


def test_create_student_sanitizes_amka_and_creates_selected_service_links(auth_client, db_session, seeded_services):
    response = auth_client.post(
        "/students/new",
        data={
            "amka": "123 456-789 99",
            "center": "Krya Vrisi",
            "first_name": "Nikos",
            "last_name": "Ioannou",
            "date_of_birth": "2016-01-10",
            "parent_name": "Maria Ioannou",
            "parent_phone": "6999999999",
            "assessment_expiry_date": "2026-12-20",
            "admin_comment": "Needs follow-up",
            f"sessions_{seeded_services[0].id}": "8",
            f"sessions_{seeded_services[1].id}": "-2",
            f"sessions_{seeded_services[2].id}": "abc",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/students/12345678999"

    student = db_session.query(Student).filter_by(amka="12345678999").first()
    assert student is not None
    assert student.center == "KryaVrisi"
    assert student.first_name == "Nikos"
    assert student.last_name == "Ioannou"

    links = (
        db_session.query(StudentService)
        .filter(StudentService.student_amka == "12345678999")
        .order_by(StudentService.service_id.asc())
        .all()
    )
    assert len(links) == 3
    assert links[0].total_sessions == 8
    assert links[1].total_sessions == 0
    assert links[2].total_sessions == 0


def test_create_student_rejects_missing_required_fields(auth_client):
    response = auth_client.post(
        "/students/new",
        data={"amka": "", "first_name": "", "last_name": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/students/new?error=1"


def test_create_student_rejects_duplicate_amka(auth_client, db_session, seeded_student):
    response = auth_client.post(
        "/students/new",
        data={
            "amka": seeded_student.amka,
            "center": "Giannitsa",
            "first_name": "Other",
            "last_name": "Student",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/students/new?exists=1"
    assert db_session.query(Student).filter_by(amka=seeded_student.amka).count() == 1


def test_edit_student_comment_trims_whitespace_and_persists(auth_client, db_session, seeded_student):
    response = auth_client.post(
        f"/students/{seeded_student.amka}/comment/edit",
        data={"admin_comment": "   Updated note   "},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db_session.refresh(seeded_student)
    assert seeded_student.admin_comment == "Updated note"


def test_add_payment_parses_decimal_with_comma(auth_client, db_session, seeded_student):
    response = auth_client.post(
        f"/students/{seeded_student.amka}/payments/new",
        data={"payment_date": "2026-03-05", "amount": "25,50", "comment": "March"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    payment = db_session.query(Payment).filter(Payment.student_amka == seeded_student.amka).first()
    assert payment is not None
    assert payment.amount_cents == 2550
    assert payment.payment_date == date(2026, 3, 5)
    assert payment.comment == "March"


def test_add_payment_rejects_bad_amount(auth_client, seeded_student):
    response = auth_client.post(
        f"/students/{seeded_student.amka}/payments/new",
        data={"payment_date": "2026-03-05", "amount": "not-a-number", "comment": "x"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/students/{seeded_student.amka}?pay_error=bad_amount"


def test_add_payment_rejects_bad_date(auth_client, seeded_student):
    response = auth_client.post(
        f"/students/{seeded_student.amka}/payments/new",
        data={"payment_date": "31/02/2026", "amount": "25.00", "comment": "x"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/students/{seeded_student.amka}?pay_error=bad_date"


@pytest.mark.xfail(reason="Known bug in route: edit_payment uses undefined variable pay_d", strict=False)
def test_edit_payment_updates_existing_payment(auth_client, db_session, seeded_student, payment_factory):
    payment = payment_factory(seeded_student.amka, amount_cents=1000, payment_date=date(2026, 3, 1), comment="old")
    response = auth_client.post(
        f"/students/{seeded_student.amka}/payments/{payment.id}/edit",
        data={"payment_date": "2026-03-10", "amount": "11.40", "comment": "updated"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db_session.refresh(payment)
    assert payment.amount_cents == 1140
    assert payment.payment_date == date(2026, 3, 10)
    assert payment.comment == "updated"


def test_delete_student_removes_student_appointments_and_payments(auth_client, db_session, seeded_student, helper_create_appointment, payment_factory, seeded_services):
    helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[0].id,
        day=date(2026, 3, 16),
        start_time_value=time(10, 0),
    )
    payment_factory(seeded_student.amka, amount_cents=3000)

    response = auth_client.post(f"/students/{seeded_student.amka}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/students"

    assert db_session.query(Student).filter_by(amka=seeded_student.amka).first() is None
    assert db_session.query(Appointment).filter_by(student_amka=seeded_student.amka).count() == 0
    assert db_session.query(Payment).filter_by(student_amka=seeded_student.amka).count() == 0
    assert db_session.query(StudentService).filter_by(student_amka=seeded_student.amka).count() == 0
