# Αυτό είναι το κύριο router της εφαρμογής. Το GET /students δείχνει μόνο το dataset 
# που αντιστοιχεί στον χρήστη. Το GET /students/{id} επιστρέφει και τις υπηρεσίες με join. 
# Τα create/update/delete είναι admin-only από τη λογική που έχουμε βάλει 
# (ο demo δεν επιτρέπεται να αλλάζει πραγματικά δεδομένα). 
# Τα notes μπορούν να τα προσθέτουν και admin και demo, αλλά πάντα στο δικό τους dataset. 
# Το endpoint PUT /students/{id}/services/{service_code} κάνει upsert (δημιουργεί ή ενημερώνει) 
# τις συνεδρίες για μια υπηρεσία στον μαθητή, και αυτό γίνεται dataset-safe.

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Student, Note, User, Service, StudentService
from ..schemas import (
    StudentCreate, StudentUpdate, StudentOut, StudentDetailOut,
    NoteCreate, NoteOut, StudentServiceUpsert
)
from ..deps import get_current_user, resolve_dataset

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = resolve_dataset(user)
    return db.query(Student).filter(Student.dataset == ds).order_by(Student.full_name).all()

@router.get("/{student_id}", response_model=StudentDetailOut)
def get_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = resolve_dataset(user)
    st = db.query(Student).filter(Student.id == student_id, Student.dataset == ds).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    # services join
    rows = (
        db.query(StudentService, Service)
        .join(Service, StudentService.service_id == Service.id)
        .filter(StudentService.student_id == student_id, StudentService.dataset == ds)
        .all()
    )

    services_out = [
        {
            "code": svc.code,
            "title": svc.title,
            "sessions_total": stsvc.sessions_total,
            "sessions_used": stsvc.sessions_used,
        }
        for stsvc, svc in rows
    ]

    data = StudentDetailOut.model_validate(st)
    data.services = services_out
    return data

@router.post("", response_model=StudentOut)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "demo":
        raise HTTPException(status_code=403, detail="Demo cannot create students")

    st = Student(
        dataset="real",
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        parent_name=payload.parent_name,
        parent_phone=payload.parent_phone,
        payment_date=payload.payment_date,
        assessment_expiry_date=payload.assessment_expiry_date,
        admin_comment=payload.admin_comment,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st

@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "demo":
        raise HTTPException(status_code=403, detail="Demo cannot edit students")

    st = db.query(Student).filter(Student.id == student_id, Student.dataset == "real").first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.full_name is not None:
        st.full_name = payload.full_name
    if payload.date_of_birth is not None:
        st.date_of_birth = payload.date_of_birth
    if payload.parent_name is not None:
        st.parent_name = payload.parent_name
    if payload.parent_phone is not None:
        st.parent_phone = payload.parent_phone
    if payload.payment_date is not None:
        st.payment_date = payload.payment_date
    if payload.assessment_expiry_date is not None:
        st.assessment_expiry_date = payload.assessment_expiry_date
    if payload.admin_comment is not None:
        st.admin_comment = payload.admin_comment

    st.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(st)
    return st

@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "demo":
        raise HTTPException(status_code=403, detail="Demo cannot delete students")

    st = db.query(Student).filter(Student.id == student_id, Student.dataset == "real").first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(st)
    db.commit()
    return {"ok": True}

# ----- Notes -----
@router.get("/{student_id}/notes", response_model=list[NoteOut])
def list_notes(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = resolve_dataset(user)

    exists = db.query(Student).filter(Student.id == student_id, Student.dataset == ds).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Student not found")

    return (
        db.query(Note)
        .filter(Note.student_id == student_id, Note.dataset == ds)
        .order_by(Note.created_at.desc())
        .all()
    )

@router.post("/{student_id}/notes", response_model=NoteOut)
def add_note(student_id: int, payload: NoteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = resolve_dataset(user)

    exists = db.query(Student).filter(Student.id == student_id, Student.dataset == ds).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Student not found")

    note = Note(dataset=ds, student_id=student_id, author_user_id=user.id, text=payload.text)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

# ----- Services per student (upsert) -----
@router.put("/{student_id}/services/{service_code}")
def upsert_student_service(
    student_id: int,
    service_code: str,
    payload: StudentServiceUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ds = resolve_dataset(user)

    # demo: επιτρέπουμε να αλλάζει ΜΟΝΟ demo dataset, admin ΜΟΝΟ real
    st = db.query(Student).filter(Student.id == student_id, Student.dataset == ds).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    svc = db.query(Service).filter(Service.code == service_code).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    row = (
        db.query(StudentService)
        .filter(StudentService.dataset == ds, StudentService.student_id == student_id, StudentService.service_id == svc.id)
        .first()
    )

    if row is None:
        row = StudentService(dataset=ds, student_id=student_id, service_id=svc.id)

    row.sessions_total = payload.sessions_total
    row.sessions_used = payload.sessions_used

    db.add(row)
    db.commit()
    return {"ok": True}
