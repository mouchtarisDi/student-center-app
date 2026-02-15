from sqlalchemy.orm import Session

from .models import User, Service
from .security import hash_password


def seed_users(db: Session):
    if db.query(User).count() > 0:
        return

    db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin", is_active=1))
    db.add(User(username="demo", password_hash=hash_password("demo123"), role="demo", is_active=1))
    db.commit()


def seed_services(db: Session):
    existing = {
        s.name for s in db.query(Service.name).all()
    }

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


def seed_all(db: Session):
    seed_users(db)
    seed_services(db)