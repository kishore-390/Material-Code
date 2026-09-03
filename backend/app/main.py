import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base  # noqa: F401 - registers the full model set before any query runs
from app.db.init_db import init_extensions

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered CPSE Material Harmonization Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        init_extensions()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("Could not initialize DB extensions on startup: %s", exc)


os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "project": "ONE NATION - ONE COMMON MATERIAL CODE",
        "description": "AI-Powered CPSE Material Harmonization Platform",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
