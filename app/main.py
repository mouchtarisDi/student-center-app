from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import Base, engine, SessionLocal
from .seed import seed_all
from .routers import auth, web

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent  # .../app
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


init_db()

app.include_router(auth.router)
app.include_router(web.router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)