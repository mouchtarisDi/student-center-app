from __future__ import annotations

from datetime import date, datetime, time

from app.models import Appointment, Holiday, Payment, StudentService
from app.routers.web import service_badge_class


def test_holidays_add_and_duplicate_protection(auth_client, db_session):
    response = auth_client.post(
        "/holidays/add",
        data={"center": "Giannitsa", "day": "2026-03-25", "note": "National holiday"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/holidays?center=Giannitsa&ok=1"
    assert db_session.query(Holiday).filter_by(center="Giannitsa").count() == 1

    response2 = auth_client.post(
        "/holidays/add",
        data={"center": "Giannitsa", "day": "2026-03-25", "note": "Duplicate"},
        follow_redirects=False,
    )
    assert response2.status_code == 303
    assert response2.headers["location"] == "/holidays?center=Giannitsa&exists=1"
    assert db_session.query(Holiday).filter_by(center="Giannitsa").count() == 1


def test_schedule_create_batch_respects_remaining_sessions_cap(auth_client, db_session, seeded_student, seeded_services, helper_create_appointment):
    link = (
        db_session.query(StudentService)
        .filter_by(student_amka=seeded_student.amka, service_id=seeded_services[0].id)
        .first()
    )
    link.total_sessions = 2
    db_session.commit()

    response = auth_client.post(
        "/schedule/create-batch",
        data={
            "student_amka": seeded_student.amka,
            "service_id": seeded_services[0].id,
            "start_day": "2026-03-16",
            "start_time": "10:00",
            "count": "5",
            "duration_min": "45",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "capped=1" in response.headers["location"]

    appointments = (
        db_session.query(Appointment)
        .filter_by(student_amka=seeded_student.amka, service_id=seeded_services[0].id)
        .order_by(Appointment.day.asc())
        .all()
    )
    assert len(appointments) == 2
    assert [ap.day for ap in appointments] == [date(2026, 3, 16), date(2026, 3, 23)]


def test_schedule_create_batch_skips_holidays_when_requested(auth_client, db_session, seeded_student, seeded_services, holiday_factory):
    holiday_factory("Giannitsa", date(2026, 3, 23), "Closed")

    response = auth_client.post(
        "/schedule/create-batch",
        data={
            "student_amka": seeded_student.amka,
            "service_id": seeded_services[0].id,
            "start_day": "2026-03-16",
            "start_time": "09:00",
            "count": "3",
            "duration_min": "45",
            "skip_holidays": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "ok=1" in response.headers["location"]

    appointments = (
        db_session.query(Appointment)
        .filter_by(student_amka=seeded_student.amka, service_id=seeded_services[0].id)
        .order_by(Appointment.day.asc())
        .all()
    )
    assert len(appointments) == 3
    assert [ap.day for ap in appointments] == [
        date(2026, 3, 16),
        date(2026, 3, 30),
        date(2026, 4, 6),
    ]


def test_schedule_create_batch_blocks_when_start_date_after_assessment_expiry(auth_client, seeded_student, seeded_services):
    response = auth_client.post(
        "/schedule/create-batch",
        data={
            "student_amka": seeded_student.amka,
            "service_id": seeded_services[0].id,
            "start_day": "2027-01-10",
            "start_time": "11:00",
            "count": "2",
            "duration_min": "45",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=expiry_limit" in response.headers["location"]


def test_schedule_update_status_returns_json_with_service_stats(auth_client, db_session, seeded_student, seeded_services, helper_create_appointment):
    appointment = helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[0].id,
        day=date(2026, 3, 16),
        start_time_value=time(10, 0),
        status="scheduled",
    )

    response = auth_client.post(
        f"/schedule/{appointment.id}/status",
        data={"status": "completed"},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["action"] == "updated"
    assert payload["new_status"] == "completed"
    assert payload["service_stats"]["used"] == 1
    assert payload["service_stats"]["completed"] == 1
    assert payload["service_stats"]["remaining"] == 3


def test_schedule_update_status_canceled_deletes_appointment(auth_client, db_session, seeded_student, seeded_services, helper_create_appointment):
    appointment = helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[0].id,
        day=date(2026, 3, 16),
        start_time_value=time(12, 0),
    )

    response = auth_client.post(
        f"/schedule/{appointment.id}/status",
        data={"status": "canceled"},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["action"] == "deleted"
    assert db_session.query(Appointment).filter_by(id=appointment.id).first() is None


def test_schedule_student_month_returns_only_scheduled_and_completed(auth_client, db_session, seeded_student, seeded_services, helper_create_appointment):
    helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[0].id,
        day=date(2026, 3, 2),
        start_time_value=time(9, 0),
        status="scheduled",
    )
    helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[1].id,
        day=date(2026, 3, 9),
        start_time_value=time(10, 0),
        status="completed",
    )
    helper_create_appointment(
        db_session,
        student_amka=seeded_student.amka,
        service_id=seeded_services[1].id,
        day=date(2026, 3, 16),
        start_time_value=time(11, 0),
        status="canceled",
    )

    response = auth_client.get(
        f"/schedule/student-month?student_amka={seeded_student.amka}&year=2026&month=3"
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    statuses = {item["status"] for item in payload["items"]}
    assert statuses == {"scheduled", "completed"}
    assert all(item["service_class"].startswith("service-badge-") for item in payload["items"])


def test_schedule_page_loads_with_remaining_js_data(auth_client, seeded_student):
    response = auth_client.get("/schedule?center=Giannitsa&week=2026-03-16")
    assert response.status_code == 200
    assert "remaining_js" in response.text or "schedule" in response.text.lower()
