# Οι routers είναι ο τρόπος που οργανώνουμε τα endpoints. 
# Χωρίζουμε auth endpoints από student endpoints και demo endpoints 
# ώστε να είναι καθαρό το API και ευανάγνωστο. 
# Κάθε router έχει prefix (/auth, /students, /demo) και tags ώστε να εμφανίζεται σωστά στο Swagger. 
# Το σημαντικό είναι ότι τα endpoints “κλειδώνουν” με Depends(get_current_user), 
# άρα χωρίς token παίρνεις 401. Το dataset isolation εφαρμόζεται σε κάθε query μέσω resolve_dataset(user).

# Αυτό το router υλοποιεί το login. Παίρνει username/password, βρίσκει τον χρήστη, 
# ελέγχει bcrypt hash, και επιστρέφει JWT token. Από εκεί και πέρα ο client θα στέλνει 
# το token στο Authorization header.

from fastapi import APIRouter, Depends, Form, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/web-login")
def web_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login?error=1", status_code=303)

    if not verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=1", status_code=303)

    token = create_access_token(subject=user.username, role=user.role)

    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60,
    )
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp
