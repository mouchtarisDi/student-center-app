import os
from sqlalchemy.orm import Session

from .models import User, Service
from .security import hash_password


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

    # Αν δεν υπήρχε τίποτα να γίνει, δεν πειράζει, απλά commit δεν “πονάει”
    db.commit()

    print("SEED_USERS RUNNING")
    print("ADMIN_USERNAME:", os.getenv("ADMIN_USERNAME"))
    print("ADMIN_PASSWORD SET:", bool(os.getenv("ADMIN_PASSWORD")))

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


def seed_all(db: Session) -> None:
    seed_users(db)
    seed_services(db)