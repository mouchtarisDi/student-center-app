# Οι routers είναι ο τρόπος που οργανώνουμε τα endpoints. 
# Χωρίζουμε auth endpoints από student endpoints και demo endpoints 
# ώστε να είναι καθαρό το API και ευανάγνωστο. 
# Κάθε router έχει prefix (/auth, /students, /demo) και tags ώστε να εμφανίζεται σωστά στο Swagger. 
# Το σημαντικό είναι ότι τα endpoints “κλειδώνουν” με Depends(get_current_user), 
# άρα χωρίς token παίρνεις 401. Το dataset isolation εφαρμόζεται σε κάθε query μέσω resolve_dataset(user).

# Αυτό το router υλοποιεί το login. Παίρνει username/password, βρίσκει τον χρήστη, 
# ελέγχει bcrypt hash, και επιστρέφει JWT token. Από εκεί και πέρα ο client θα στέλνει 
# το token στο Authorization header.
from __future__ import annotations

import os
import time
from fastapi import APIRouter, Depends, Form, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Brute force protection (απλό, in-memory) ---
# ip -> (fail_count, blocked_until_epoch_seconds)
FAILED_LOGINS: dict[str, tuple[int, float]] = {}
MAX_FAILS = 5
BLOCK_SECONDS = 60


def _cookie_secure() -> bool:
    """
    Σε production (HTTPS) θέλουμε secure cookies.
    Στο Render βάλε COOKIE_SECURE=1.
    Τοπικά άστο κενό ή 0 αν θες να δουλεύει και σε http://localhost.
    """
    v = os.getenv("COOKIE_SECURE", "").strip()
    if v == "":
        env = os.getenv("ENV", os.getenv("APP_ENV", "dev")).lower().strip()
        return env in {"prod", "production"}
    return v not in {"0", "false", "False", "no", "NO"}


def _client_ip(request: Request) -> str:
    # Local/dev: request.client.host είναι αρκετό.
    # Behind proxy (Render), συνήθως προωθείται X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # μπορεί να είναι "ip1, ip2, ..."
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/web-login")
def web_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    now = time.time()

    fail_count, blocked_until = FAILED_LOGINS.get(ip, (0, 0.0))
    if now < blocked_until:
        # ακόμα μπλοκαρισμένος
        return RedirectResponse(url="/login?error=1", status_code=303)

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        # αποτυχία login -> μέτρα attempt
        fail_count += 1
        if fail_count >= MAX_FAILS:
            FAILED_LOGINS[ip] = (fail_count, now + BLOCK_SECONDS)
        else:
            FAILED_LOGINS[ip] = (fail_count, 0.0)
        return RedirectResponse(url="/login?error=1", status_code=303)

    if not verify_password(password, user.password_hash):
        fail_count += 1
        if fail_count >= MAX_FAILS:
            FAILED_LOGINS[ip] = (fail_count, now + BLOCK_SECONDS)
        else:
            FAILED_LOGINS[ip] = (fail_count, 0.0)
        return RedirectResponse(url="/login?error=1", status_code=303)

    # επιτυχές login -> καθάρισμα αποτυχιών
    FAILED_LOGINS.pop(ip, None)

    token = create_access_token(subject=user.username, role=user.role)

    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
        max_age=60 * 60 * 12,
    )
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token", path="/")
    return resp