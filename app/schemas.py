from datetime import datetime, date
from pydantic import BaseModel, Field

# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Students ----------
class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date | None = None

    parent_name: str | None = Field(default=None, max_length=120)
    parent_phone: str | None = Field(default=None, max_length=40)

    payment_date: date | None = None
    assessment_expiry_date: date | None = None

    admin_comment: str | None = Field(default=None, max_length=4000)

class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    date_of_birth: date | None = None

    parent_name: str | None = Field(default=None, max_length=120)
    parent_phone: str | None = Field(default=None, max_length=40)

    payment_date: date | None = None
    assessment_expiry_date: date | None = None

    admin_comment: str | None = Field(default=None, max_length=4000)

class StudentOut(BaseModel):
    id: int
    dataset: str
    full_name: str
    date_of_birth: date | None
    parent_name: str | None
    parent_phone: str | None
    payment_date: date | None
    assessment_expiry_date: date | None
    admin_comment: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Services for a student ----------
class StudentServiceUpsert(BaseModel):
    sessions_total: int = Field(ge=0, default=0)
    sessions_used: int = Field(ge=0, default=0)

class StudentServiceOut(BaseModel):
    code: str
    title: str
    sessions_total: int
    sessions_used: int


# ---------- Student Details (student + services) ----------
class StudentDetailOut(StudentOut):
    services: list[StudentServiceOut] = []


# ---------- Notes ----------
class NoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class NoteOut(BaseModel):
    id: int
    dataset: str
    student_id: int
    author_user_id: int | None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True
