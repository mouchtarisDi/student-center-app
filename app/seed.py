import os
from sqlalchemy.orm import Session

from .models import User, Service
from .security import hash_password


def seed_users(db: Session) -> None:

    if db.query(User).count() > 0:
        return

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    demo_username = os.getenv("DEMO_USERNAME", "demo")
    demo_password = os.getenv("DEMO_PASSWORD", "demo123")

    db.add(
        User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="admin",
            is_active=1,
        )
    )
    db.add(
        User(
            username=demo_username,
            password_hash=hash_password(demo_password),
            role="demo",
            is_active=1,
        )
    )
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


def seed_all(db: Session) -> None:
    seed_users(db)
    seed_services(db)