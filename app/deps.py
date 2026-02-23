# app/deps.py
from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_access_token


def _get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def require_user(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    token = _get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=307, detail="redirect:/login")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=307, detail="redirect:/login")

    username = payload["sub"]
    role = payload.get("role")

    user = db.query(User).filter(User.username == username, User.is_active == 1).first()
    if not user:
        raise HTTPException(status_code=307, detail="redirect:/login")

    return {"username": username, "role": role}


def require_admin(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


def redirect_middleware_handler(request: Request, exc: HTTPException):
    if exc.status_code == 307 and isinstance(exc.detail, str) and exc.detail.startswith("redirect:"):
        url = exc.detail.split("redirect:", 1)[1]
        return RedirectResponse(url=url, status_code=303)
    return None


# ✅ Αυτό είναι που λείπει και σου βγάζει ImportError:
get_current_user = require_user