from __future__ import annotations

from datetime import date, datetime

from app.routers.web import (
    _remaining_sessions,
    fmt_date_gr,
    normalize_center,
    parse_date,
    parse_time_hhmm,
    service_badge_class,
    start_of_week,
)


class DummyObj:
    pass


def test_normalize_center_handles_known_and_unknown_values():
    assert normalize_center("Giannitsa") == "Giannitsa"
    assert normalize_center("KryaVrisi") == "KryaVrisi"
    assert normalize_center("Krya Vrisi") == "KryaVrisi"
    assert normalize_center("unknown") == "Giannitsa"
    assert normalize_center(None) == "Giannitsa"


def test_parse_date_accepts_iso_and_greek_formats_and_rejects_bad_values():
    assert parse_date("2026-03-16") == date(2026, 3, 16)
    assert parse_date("16/03/2026") == date(2026, 3, 16)
    assert parse_date(" 16/03/2026 ") == date(2026, 3, 16)
    assert parse_date("") is None
    assert parse_date("31/02/2026") is None
    assert parse_date("2026/03/16") is None


def test_parse_time_hhmm_handles_valid_and_invalid_cases():
    assert parse_time_hhmm("09:30").strftime("%H:%M") == "09:30"
    assert parse_time_hhmm(" 14:05 ").strftime("%H:%M") == "14:05"
    assert parse_time_hhmm("") is None
    assert parse_time_hhmm("25:00") is None
    assert parse_time_hhmm("9.30") is None


def test_start_of_week_returns_monday():
    assert start_of_week(date(2026, 3, 16)) == date(2026, 3, 16)  # Monday
    assert start_of_week(date(2026, 3, 18)) == date(2026, 3, 16)  # Wednesday
    assert start_of_week(date(2026, 3, 22)) == date(2026, 3, 16)  # Sunday


def test_format_date_greek_or_dash():
    assert fmt_date_gr(date(2026, 3, 16)) == "16/03/2026"
    assert fmt_date_gr(None) == "-"


def test_service_badge_class_covers_multiple_keywords():
    assert service_badge_class("Speech Therapy") == "service-badge-speech"
    assert service_badge_class("Λογοθεραπεία") == "service-badge-speech"
    assert service_badge_class("Occupational Therapy") == "service-badge-occupational"
    assert service_badge_class("Ψυχολόγος") == "service-badge-psychology"
    assert service_badge_class("Unmapped Service") == "service-badge-default"


def test_remaining_sessions_supports_multiple_field_variants():
    a = DummyObj()
    a.remaining_sessions = 7
    assert _remaining_sessions(a) == 7

    b = DummyObj()
    b.total_sessions = 10
    b.used_sessions = 4
    assert _remaining_sessions(b) == 6

    c = DummyObj()
    c.sessions_total = 8
    c.sessions_used = 3
    assert _remaining_sessions(c) == 5

    d = DummyObj()
    assert _remaining_sessions(d) == -1
