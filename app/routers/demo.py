# Αυτό το router υλοποιεί το Reset Demo. Η ουσία εδώ είναι ότι σβήνουμε μόνο rows με dataset="demo" 
# και μετά ξανατρέχουμε το seed_demo_data. Έτσι ο demo χρήστης μπορεί να κάνει αλλαγές 
# (π.χ. notes ή sessions) και να τις κρατάει μέχρι να πατήσει Reset. 
# Το πιο σημαντικό είναι ότι δεν υπάρχει περίπτωση να αγγίξει real δεδομένα, 
# γιατί το query φιλτράρει αποκλειστικά dataset="demo".

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Student, Note, StudentService, User
from ..deps import get_current_user
from ..seed import seed_demo_data

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # σβήνει ΜΟΝΟ demo
    db.query(Note).filter(Note.dataset == "demo").delete()
    db.query(StudentService).filter(StudentService.dataset == "demo").delete()
    db.query(Student).filter(Student.dataset == "demo").delete()
    db.commit()

    seed_demo_data(db)
    return {"ok": True}
