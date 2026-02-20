from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from calendar import monthrange

from fastapi import APIRouter, Depends, Form, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from ..db import get_db
from ..deps import get_current_user
from ..models import (
    User,
    Student,
    Service,
    StudentService,
    Appointment,
    Payment,
    Holiday,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# Constants / helpers
# -----------------------------
CENTERS: dict[str, str] = {
    "Giannitsa": "Γιαννιτσά",
    "KryaVrisi": "Κρύα Βρύση",
    # backwards compatibility
    "Krya Vrisi": "Κρύα Βρύση",
}


def normalize_center(center: str | None) -> str:
    c = (center or "").strip()
    if c == "Krya Vrisi":
        return "KryaVrisi"
    if c not in {"Giannitsa", "KryaVrisi"}:
        return "Giannitsa"
    return c


def fmt_date_gr(d: date | None) -> str:
    if not d:
        return "-"
    return d.strftime("%d/%m/%Y")


templates.env.globals["fmt_date_gr"] = fmt_date_gr


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_time_hhmm(s: str) -> time | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        return None


def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def is_holiday(db: Session, center: str, d: date) -> bool:
    center = normalize_center(center)
    return (
        db.query(Holiday.id)
        .filter(Holiday.center == center)
        .filter(Holiday.day == d)
        .first()
        is not None
    )

def _remaining_sessions(ss: StudentService) -> int:
    """
    Επιστρέφει πόσες συνεδρίες απομένουν για το συγκεκριμένο StudentService.
    Προσαρμόζεται σε διαφορετικά πιθανά ονόματα πεδίων.
    """
    # Variant A: έχεις αποθηκευμένο "remaining_sessions"
    if hasattr(ss, "remaining_sessions") and ss.remaining_sessions is not None:
        return int(ss.remaining_sessions)

    # Variant B: έχεις total/used
    total = None
    used = None

    for name in ("total_sessions", "sessions_total", "allowed_sessions", "sessions_allowed"):
        if hasattr(ss, name) and getattr(ss, name) is not None:
            total = int(getattr(ss, name))
            break

    for name in ("used_sessions", "sessions_used", "completed_sessions", "consumed_sessions"):
        if hasattr(ss, name) and getattr(ss, name) is not None:
            used = int(getattr(ss, name))
            break

    if total is not None and used is not None:
        return max(0, total - used)

    # Αν δεν βρούμε τίποτα, καλύτερα να μπλοκάρουμε (fail-safe)
    return -1

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# -----------------------------
# Dashboard
# -----------------------------
@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    exp_limit = today + timedelta(days=30)

    centers_order = ["Giannitsa", "KryaVrisi"]
    centers_labels = {
        "Giannitsa": CENTERS.get("Giannitsa", "Giannitsa"),
        "KryaVrisi": CENTERS.get("KryaVrisi", "KryaVrisi"),
    }

    # ---- Students per center ----
    student_counts_by_center = {}
    for c in centers_order:
        student_counts_by_center[c] = (
            db.query(Student)
            .filter(Student.center == c)
            .count()
        )

    # ---- Reports expiring per center (within 30 days) ----
    reports_list_by_center = {}
    reports_expiring_by_center = {}

    for c in centers_order:
        reports = (
            db.query(Student)
            .filter(Student.center == c)
            .filter(Student.assessment_expiry_date.isnot(None))
            .filter(Student.assessment_expiry_date >= today)
            .filter(Student.assessment_expiry_date <= exp_limit)
            .order_by(Student.assessment_expiry_date.asc())
            .all()
        )
        reports_list_by_center[c] = reports
        reports_expiring_by_center[c] = len(reports)

    # ---- Today's program per center ----
    todays_by_center = {}
    for c in centers_order:
        todays_by_center[c] = (
            db.query(Appointment)
            .options(
                joinedload(Appointment.student),
                joinedload(Appointment.service),
            )
            .filter(Appointment.center == c)
            .filter(Appointment.day == today)
            .filter(Appointment.status == "scheduled")
            .order_by(Appointment.start_time.asc())
            .all()
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "page": "dashboard",
            "today": today,
            "exp_limit": exp_limit,
            "centers_order": centers_order,
            "centers_labels": centers_labels,
            "student_counts_by_center": student_counts_by_center,
            "reports_list_by_center": reports_list_by_center,
            "reports_expiring_by_center": reports_expiring_by_center,
            "todays_by_center": todays_by_center,
        },
    )


# -----------------------------
# Students list
# -----------------------------
@router.get("/students", response_class=HTMLResponse)
def students_page(
    request: Request,
    center: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    center_norm = normalize_center(center) if center else None

    q = db.query(Student)
    if center_norm:
        q = q.filter(Student.center == center_norm)

    students = q.order_by(Student.last_name.asc(), Student.first_name.asc()).all()

    return templates.TemplateResponse(
        "students.html",
        {
            "request": request,
            "user": user,
            "page": "students",
            "students": students,
            "centers": CENTERS,
        },
    )


# -----------------------------
# Add student (GET)
# -----------------------------
@router.get("/students/new", response_class=HTMLResponse)
def student_new_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    services = db.query(Service).order_by(Service.name.asc()).all()

    return templates.TemplateResponse(
        "student_new.html",
        {
            "request": request,
            "user": user,
            "page": "students",
            "services": services,
            "centers": CENTERS,
        },
    )


# -----------------------------
# Add student (POST)
# -----------------------------
@router.post("/students/new")
async def student_create(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()

    amka = (form.get("amka") or "").strip()
    center = normalize_center(form.get("center") or "Giannitsa")

    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()

    dob = parse_date(form.get("date_of_birth") or "")
    parent_name = (form.get("parent_name") or "").strip() or None
    parent_phone = (form.get("parent_phone") or "").strip() or None

    assessment_expiry_date = parse_date(form.get("assessment_expiry_date") or "")
    admin_comment = (form.get("admin_comment") or "").strip() or None

    if not amka or not first_name or not last_name:
        return RedirectResponse("/students/new?error=1", status_code=303)

    st = Student(
        amka=amka,
        center=center,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob,
        parent_name=parent_name,
        parent_phone=parent_phone,
        assessment_expiry_date=assessment_expiry_date,
        admin_comment=admin_comment,
    )
    db.add(st)

    services = db.query(Service).all()
    for svc in services:
        key = f"sessions_{svc.id}"
        raw = (form.get(key) or "").strip()
        if not raw:
            continue
        try:
            n = int(raw)
        except ValueError:
            n = 0
        if n < 0:
            n = 0

        link = StudentService(student_amka=amka, service_id=svc.id, total_sessions=n)
        db.add(link)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse("/students/new?exists=1", status_code=303)

    return RedirectResponse(f"/students/{amka}", status_code=303)


# -----------------------------
# Student page
# -----------------------------
@router.get("/students/{amka}", response_class=HTMLResponse)
def student_page(
    amka: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = db.query(Student).filter(Student.amka == amka).first()
    if not st:
        return RedirectResponse("/students", status_code=303)

    links = (
        db.query(StudentService)
        .filter(StudentService.student_amka == amka)
        .all()
    )

    services_info = []
    for l in links:
        total = int(l.total_sessions or 0)

        used = (
            db.query(Appointment.id)
            .filter(Appointment.student_amka == amka)
            .filter(Appointment.service_id == l.service_id)
            .filter(Appointment.status.in_(["scheduled", "completed"]))
            .count()
        )

        completed = (
            db.query(Appointment.id)
            .filter(Appointment.student_amka == amka)
            .filter(Appointment.service_id == l.service_id)
            .filter(Appointment.status == "completed")
            .count()
        )

        remaining = max(total - int(used), 0)

        services_info.append(
            {
                "service": l.service,
                "total": total,
                "completed": int(completed),
                "remaining": int(remaining),
            }
        )

    appointments = (
        db.query(Appointment)
        .filter(Appointment.student_amka == amka)
        .order_by(Appointment.day.desc(), Appointment.start_time.desc())
        .all()
    )

    payments = (
        db.query(Payment)
        .filter(Payment.student_amka == amka)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        "student_page.html",
        {
            "request": request,
            "user": user,
            "page": "students",
            "student": st,
            "services_info": services_info,
            "appointments": appointments,
            "payments": payments,
            "today": date.today(),
            "centers": CENTERS,
        },
    )


# -----------------------------
# Add payment
# -----------------------------
@router.post("/students/{amka}/payments/new")
def payment_create(
    amka: str,
    payment_date: str = Form(...),
    amount: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = db.query(Student).filter(Student.amka == amka).first()
    if not st:
        return RedirectResponse("/students", status_code=303)

    d = parse_date(payment_date)
    if not d:
        return RedirectResponse(f"/students/{amka}?pay_error=1", status_code=303)

    a = (amount or "").strip().replace(",", ".")
    try:
        cents = int(round(float(a) * 100))
    except ValueError:
        return RedirectResponse(f"/students/{amka}?pay_error=1", status_code=303)

    p = Payment(
        student_amka=amka,
        payment_date=d,
        amount_cents=cents,
        comment=(comment or "").strip() or None,
    )
    db.add(p)
    db.commit()

    return RedirectResponse(f"/students/{amka}", status_code=303)


@router.post("/students/{amka}/assessment/renew")
def renew_assessment(
    amka: str,
    assessment_expiry_date: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = db.query(Student).filter(Student.amka == amka).first()
    if not st:
        return RedirectResponse("/students", status_code=303)

    d = parse_date(assessment_expiry_date)
    if not d:
        return RedirectResponse(f"/students/{amka}?renew_error=1", status_code=303)

    st.assessment_expiry_date = d
    db.commit()

    return RedirectResponse(f"/students/{amka}?renew_ok=1", status_code=303)


# -----------------------------
# Schedule (weekly view)
# -----------------------------
@router.get("/schedule", response_class=HTMLResponse)
def schedule_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    center: str | None = None,
    week: str | None = None,
):
    today = date.today()
    base = parse_date(week or "") or today
    week_start = start_of_week(base)
    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    # Mon..Sat (6 μέρες)
    days = []
    labels = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο"]
    for i in range(6):
        d = week_start + timedelta(days=i)
        days.append(
            {
                "label": labels[i],
                "date": d,
                "date_iso": d.isoformat(),
                "date_str": d.strftime("%d/%m/%Y"),
            }
        )

    center = normalize_center(center) if center else "Giannitsa"
    week_end = week_start + timedelta(days=5)

    # ✅ Φόρτωσε appointments με student/service (για να εμφανίζονται ονόματα)
    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.student), joinedload(Appointment.service))
        .filter(Appointment.center == center)
        .filter(Appointment.day >= week_start)
        .filter(Appointment.day <= week_end)
        .filter(Appointment.status.in_(["scheduled", "completed"]))  # προαιρετικό
        .order_by(Appointment.day.asc(), Appointment.start_time.asc())
        .all()
    )
    week_days = [x["date"] for x in days]
    appointments_by_day: dict[str, list[Appointment]] = {d.isoformat(): [] for d in week_days}

    for ap in appointments:
        appointments_by_day[ap.day.isoformat()].append(ap)

    students = db.query(Student).order_by(Student.last_name.asc(), Student.first_name.asc()).all()
    services = db.query(Service).order_by(Service.name.asc()).all()

    # -------------------------------------------------
    # ✅ Remaining sessions map (για schedule.html JS)
    # remaining = total_sessions - completed
    # -------------------------------------------------
    totals = (
        db.query(
            StudentService.student_amka,
            StudentService.service_id,
            func.coalesce(StudentService.total_sessions, 0),
        )
        .all()
    )
    totals_map = {(amka, int(sid)): int(total or 0) for (amka, sid, total) in totals}

    completed = (
        db.query(
            Appointment.student_amka,
            Appointment.service_id,
            func.count(Appointment.id),
        )
        .filter(Appointment.status == "completed")
        .group_by(Appointment.student_amka, Appointment.service_id)
        .all()
    )
    completed_map = {(amka, int(sid)): int(cnt or 0) for (amka, sid, cnt) in completed}

    remaining_js_map: dict[str, int] = {}
    for (amka, sid), total in totals_map.items():
        done = completed_map.get((amka, sid), 0)
        remaining_js_map[f"{amka}|{sid}"] = max(int(total) - int(done), 0)

    remaining_js = json.dumps(remaining_js_map)

    # -------------------------------------------------
    # ✅ ΝΕΟ weekly-list data: week_days + appointments_by_day
    # -------------------------------------------------
    week_days = [x["date"] for x in days]  # list[date] (Mon..Sat)
    appointments_by_day: dict[str, list[Appointment]] = {d.isoformat(): [] for d in week_days}
    for ap in appointments:
        appointments_by_day[ap.day.isoformat()].append(ap)

    return templates.TemplateResponse(
        "schedule.html",
        {
            "request": request,
            "user": user,
            "page": "schedule",
            "students": students,
            "services": services,
            "centers": CENTERS,
            "center": center,
            "week_start": week_start,
            "week_start_str": week_start.isoformat(),
            "days": days,  # αν το χρειάζεσαι αλλού
            "remaining_js": remaining_js,
            "today": today,
            "prev_week": prev_week,
            "next_week": next_week,

            # ✅ αυτά έλειπαν και γι’ αυτό δεν έβλεπες τίποτα
            "week_days": week_days,
            "appointments_by_day": appointments_by_day,
        },
    )

@router.get("/schedule/student-month")
def schedule_student_month(
    student_amka: str = Query(...),
    year: int = Query(...),
    month: int = Query(...),  # 1-12
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # basic validation
    if month < 1 or month > 12:
        return {"items": []}

    st = db.query(Student).filter(Student.amka == student_amka).first()
    if not st:
        return {"items": []}

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    aps = (
        db.query(Appointment)
        .options(joinedload(Appointment.service))
        .filter(Appointment.student_amka == student_amka)
        .filter(Appointment.day >= first_day)
        .filter(Appointment.day <= last_day)
        .filter(Appointment.status.in_(["scheduled", "completed"]))  # αν θες, βγάλε completed/βάλε canceled
        .order_by(Appointment.day.asc(), Appointment.start_time.asc())
        .all()
    )

    items = []
    for ap in aps:
        items.append(
            {
                "day": ap.day.isoformat(),
                "time": ap.start_time.strftime("%H:%M"),
                "service": ap.service.name if ap.service else f"Service #{ap.service_id}",
                "status": ap.status,
                "id": ap.id,
            }
        )

    return {"items": items}

# -----------------------------
# Schedule batch create
# -----------------------------
@router.post("/schedule/create-batch")
def schedule_create_batch(
    student_amka: str = Form(...),
    service_id: int = Form(...),
    start_day: str = Form(...),
    start_time: str | None = Form(None),
    count: int = Form(...),
    duration_min: int = Form(45),
    skip_holidays: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = db.query(Student).filter(Student.amka == student_amka).first()
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not st or not svc:
        return RedirectResponse("/schedule?error=not_found", status_code=303)

    d0 = parse_date(start_day)
    if not d0:
        return RedirectResponse("/schedule?error=bad_date", status_code=303)

    raw_time = (start_time or "").strip()
    if raw_time:
        t0 = parse_time_hhmm(raw_time)
        if not t0:
            return RedirectResponse("/schedule?error=bad_time", status_code=303)
    else:
        t0 = time(9, 0)

    st_center = normalize_center(st.center)

    # ---- 1) Έλεγχος λήξης γνωμάτευσης ----
    expiry = st.assessment_expiry_date  # μπορεί να είναι None
    if expiry is not None and d0 > expiry:
        # αν ο χρήστης διάλεξε start_day μετά τη λήξη -> δεν γίνεται τίποτα
        return RedirectResponse(
            f"/schedule?center={st_center}&week={start_of_week(d0).isoformat()}&error=expiry_limit",
            status_code=303,
        )

    # ---- 2) Δικαιούμενες συνεδρίες (StudentService link) ----
    link = (
        db.query(StudentService)
        .filter(StudentService.student_amka == st.amka)
        .filter(StudentService.service_id == svc.id)
        .first()
    )
    if not link:
        return RedirectResponse(
            f"/schedule?center={st_center}&week={start_of_week(d0).isoformat()}&error=service_not_assigned",
            status_code=303,
        )

    total_allowed = int(link.total_sessions or 0)

    # Μετράμε ήδη scheduled+completed ώστε να μην ξεπερνάμε
    used = (
        db.query(Appointment.id)
        .filter(Appointment.student_amka == st.amka)
        .filter(Appointment.service_id == svc.id)
        .filter(Appointment.status.in_(["scheduled", "completed"]))
        .count()
    )

    remaining = max(total_allowed - int(used), 0)

    requested = max(int(count or 0), 0)
    to_create = min(requested, remaining)

    if to_create <= 0:
        return RedirectResponse(
            f"/schedule?center={st_center}&week={start_of_week(d0).isoformat()}&no_sessions=1",
            status_code=303,
        )

    skip = bool(skip_holidays)  # checked => "on"

    created = 0
    cur_day = d0

    while created < to_create:

        # ---- stop αν φτάσαμε/περάσαμε λήξη γνωμάτευσης ----
        if expiry is not None and cur_day > expiry:
            # δεν δημιουργούμε τίποτα πέρα από τη λήξη
            break

        # skip Sunday always
        if cur_day.weekday() == 6:
            cur_day = cur_day + timedelta(days=7)
            continue

        # skip holidays for student's center
        if skip and is_holiday(db, st_center, cur_day):
            cur_day = cur_day + timedelta(days=7)
            continue

        ap = Appointment(
            student_amka=st.amka,
            service_id=svc.id,
            center=st_center,
            day=cur_day,
            start_time=t0,
            duration_min=duration_min,
            status="scheduled",
        )
        db.add(ap)
        created += 1
        cur_day = cur_day + timedelta(days=7)

    # Αν δεν μπορέσαμε να δημιουργήσουμε όσες ζητήθηκαν λόγω expiry (ή άλλων skips),
    # κάνουμε commit όσες δημιουργήθηκαν και ενημερώνουμε με flag.
    db.commit()

    # Αν κόπηκε λόγω λήξης, δείχνουμε μήνυμα
    if created < to_create:
        return RedirectResponse(
            f"/schedule?center={st_center}&week={start_of_week(d0).isoformat()}&partial=1&created={created}",
            status_code=303,
        )

    return RedirectResponse(
        f"/schedule?center={st_center}&week={start_of_week(d0).isoformat()}&ok=1",
        status_code=303,
    )


# -----------------------------
# Update appointment status
# -----------------------------
@router.post("/schedule/{appointment_id}/status")
async def schedule_update_status(
    appointment_id: int,
    request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ap = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not ap:
        return RedirectResponse("/schedule", status_code=303)

    if status not in {"scheduled", "completed", "canceled"}:
        return RedirectResponse("/schedule", status_code=303)

    ap.status = status
    db.commit()

    form = await request.form()
    next_url = (form.get("next") or "").strip()
    if next_url.startswith("/"):
        return RedirectResponse(next_url, status_code=303)

    return RedirectResponse("/schedule", status_code=303)


# -----------------------------
# Holidays
# -----------------------------
@router.get("/holidays", response_class=HTMLResponse)
def holidays_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    center: str | None = None,
):
    center = normalize_center(center) if center else "Giannitsa"

    holidays = (
        db.query(Holiday)
        .filter(Holiday.center == center)
        .order_by(Holiday.day.asc())
        .all()
    )

    return templates.TemplateResponse(
        "holidays.html",
        {
            "request": request,
            "user": user,
            "page": "holidays",
            "centers": CENTERS,
            "center": center,
            "holidays": holidays,
            "today": date.today(),
        },
    )


@router.post("/holidays/add")
def holidays_add(
    center: str = Form(...),
    day: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    center = normalize_center(center)
    d = parse_date(day)

    if not d:
        return RedirectResponse("/holidays?error=1", status_code=303)

    h = Holiday(center=center, day=d, note=(note or "").strip() or None)
    db.add(h)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(f"/holidays?center={center}&exists=1", status_code=303)

    return RedirectResponse(f"/holidays?center={center}&ok=1", status_code=303)


@router.post("/holidays/delete")
def holidays_delete(
    holiday_id: int = Form(...),
    center: str = Form("Giannitsa"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    center = normalize_center(center)
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if h:
        db.delete(h)
        db.commit()
    return RedirectResponse(f"/holidays?center={center}&deleted=1", status_code=303)
