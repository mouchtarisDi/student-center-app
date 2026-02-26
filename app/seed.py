import os
from datetime import date, timedelta, time

from sqlalchemy.orm import Session

from .models import User, Service, Student, StudentService, Appointment, Payment
from .security import hash_password


def _is_demo_schema() -> bool:
    # Αν τρέχεις το DEMO service, θα έχεις DB_SCHEMA=demo
    return os.getenv("DB_SCHEMA", "").strip().lower() == "demo"


def seed_users(db: Session) -> None:
    # Αν ΔΕΝ υπάρχουν env vars, μην πειράξεις τίποτα
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

    demo_username = os.getenv("DEMO_USERNAME", "").strip()
    demo_password = os.getenv("DEMO_PASSWORD", "").strip()

    # ===== ADMIN UPSERT =====
    if admin_username and admin_password:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin = User(
                username=admin_username,
                password_hash=hash_password(admin_password),
                role="admin",
                is_active=1,
            )
            db.add(admin)
        else:
            admin.username = admin_username
            admin.password_hash = hash_password(admin_password)
            admin.is_active = 1

    # ===== DEMO UPSERT (αν το θες και για demo χρήστη) =====
    if demo_username and demo_password:
        demo = db.query(User).filter(User.role == "demo").first()
        if not demo:
            demo = User(
                username=demo_username,
                password_hash=hash_password(demo_password),
                role="demo",
                is_active=1,
            )
            db.add(demo)
        else:
            demo.username = demo_username
            demo.password_hash = hash_password(demo_password)
            demo.is_active = 1

    db.commit()


def seed_services(db: Session) -> None:
    existing = {name for (name,) in db.query(Service.name).all()}

    names = [
        "Λογοθεραπεία",
        "Εργοθεραπεία",
        "Ψυχοθεραπεία",
        "Ειδική Αγωγή",
    ]

    for name in names:
        if name not in existing:
            db.add(Service(name=name))

    db.commit()


def seed_demo_sample_data(db: Session) -> None:
    # """
    # Βάζει ενδεικτικά demo δεδομένα (μαθητές/υπηρεσίες/ραντεβού/πληρωμές)
    # ΜΟΝΟ όταν είμαστε στο schema=demo.

    # Σημείωση: επειδή στο DEMO service κάνουμε DROP SCHEMA στο startup,
    # αυτά τα δεδομένα "λήγουν" αυτόματα σε κάθε reset/restart.
    # """

    if not _is_demo_schema():
        return

    
    any_student = db.query(Student).first()
    if any_student:
        return

    # Πάρε services (πρέπει να έχουν seeded)
    services = {s.name: s for s in db.query(Service).all()}

    demo_students = [
        Student(
            amka="11111111111",
            center="Giannitsa",
            first_name="Άννα",
            last_name="Παπαδοπούλου",
            date_of_birth=date(2017, 5, 12),
            parent_name="Γιώργος Παπαδόπουλος",
            parent_phone="6900000001",
            assessment_expiry_date=date.today() + timedelta(days=60),
            admin_comment="DEMO μαθητής – ενδεικτικά δεδομένα.",
        ),
        Student(
            amka="22222222222",
            center="KryaVrisi",
            first_name="Νίκος",
            last_name="Ιωάννου",
            date_of_birth=date(2016, 9, 3),
            parent_name="Ελένη Ιωάννου",
            parent_phone="6900000002",
            assessment_expiry_date=date.today() + timedelta(days=30),
            admin_comment="DEMO μαθητής – ενδεικτικά δεδομένα.",
        ),
        Student(
            amka="33333333333",
            center="Giannitsa",
            first_name="Μαρία",
            last_name="Κωνσταντίνου",
            date_of_birth=date(2018, 1, 28),
            parent_name="Κώστας Κωνσταντίνου",
            parent_phone="6900000003",
            assessment_expiry_date=date.today() + timedelta(days=90),
            admin_comment="DEMO μαθητής – ενδεικτικά δεδομένα.",
        ),
    ]

    db.add_all(demo_students)
    db.commit()

    # StudentService (sessions) - ενδεικτικά
    def link(amka: str, service_name: str, total_sessions: int) -> None:
        svc = services.get(service_name)
        if not svc:
            return
        db.add(
            StudentService(
                student_amka=amka,
                service_id=svc.id,
                total_sessions=total_sessions,
            )
        )

    link("11111111111", "Λογοθεραπεία", 12)
    link("11111111111", "Εργοθεραπεία", 8)
    link("22222222222", "Ειδική Αγωγή", 16)
    link("33333333333", "Ψυχοθεραπεία", 6)
    db.commit()

    # Appointments - ενδεικτικά (επόμενες ημέρες)
    def appt(amka: str, service_name: str, center: str, day_offset: int, hh: int, mm: int) -> None:
        svc = services.get(service_name)
        if not svc:
            return
        db.add(
            Appointment(
                student_amka=amka,
                service_id=svc.id,
                center=center,
                day=date.today() + timedelta(days=day_offset),
                start_time=time(hh, mm),
                duration_min=45,
                status="scheduled",
            )
        )

    appt("11111111111", "Λογοθεραπεία", "Giannitsa", 1, 17, 0)
    appt("11111111111", "Εργοθεραπεία", "Giannitsa", 3, 18, 0)
    appt("22222222222", "Ειδική Αγωγή", "KryaVrisi", 2, 16, 30)
    appt("33333333333", "Ψυχοθεραπεία", "Giannitsa", 4, 19, 0)
    db.commit()

    # Payments - ενδεικτικά
    db.add_all(
        [
            Payment(
                student_amka="11111111111",
                payment_date=date.today() - timedelta(days=10),
                amount_cents=3000,
                comment="DEMO πληρωμή",
            ),
            Payment(
                student_amka="22222222222",
                payment_date=date.today() - timedelta(days=20),
                amount_cents=2500,
                comment="DEMO πληρωμή",
            ),
        ]
    )
    db.commit()


def seed_all(db: Session) -> None:
    seed_users(db)
    seed_services(db)
    seed_demo_sample_data(db)