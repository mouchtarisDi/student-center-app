from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from .db import Base, engine, SessionLocal
from .seed import seed_all
from .routers import auth, web
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException

from .deps import redirect_middleware_handler

app = FastAPI()

from fastapi import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles

app.mount("/assets", StaticFiles(directory="app/assets"), name="assets")


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    maybe_redirect = redirect_middleware_handler(request, exc)
    if maybe_redirect:
        return maybe_redirect
    # αλλιώς, default συμπεριφορά
    raise exc


BASE_DIR = Path(__file__).resolve().parent  # .../app
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(web.router)


@app.on_event("startup")
def on_startup() -> None:

    schema = os.getenv("DB_SCHEMA", "").strip()  # "prod" / "demo" / ""
    reset_demo = os.getenv("DEMO_RESET_ON_STARTUP", "0").strip() in {
        "1",
        "true",
        "True",
        "yes",
        "YES",
    }

    # Για Postgres μόνο: δημιούργησε schema (και προαιρετικά reset) πριν από το create_all
    if schema and (not str(engine.url).startswith("sqlite")):
        with engine.begin() as conn:
            if reset_demo:
                # ΠΡΟΣΟΧΗ: αυτό να είναι ΜΟΝΟ στο DEMO service (DB_SCHEMA=demo)
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    # Δημιουργία tables στο σωστό schema (λόγω search_path στο db.py)
    Base.metadata.create_all(bind=engine)

    # Seed μόνο αν είναι ενεργό (default: ναι)
    seed_enabled = os.getenv("SEED_DB_ON_STARTUP", "1").strip() not in {
        "0",
        "false",
        "False",
        "no",
        "NO",
    }
    if seed_enabled:
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()