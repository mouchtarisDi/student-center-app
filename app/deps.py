from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_access_token  # <-- ή όπως το έχεις εσύ

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Web auth: αν δεν υπάρχει token cookie ή είναι invalid,
    αντί για 401 JSON κάνουμε redirect στο /login.
    """
    token = request.cookies.get("access_token")

    if not token:
        # Browser redirect
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    payload = decode_access_token(token)  # πρέπει να επιστρέφει dict ή None
    if not payload:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    username = payload.get("sub") or payload.get("subject") or payload.get("username")
    if not username:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return user
