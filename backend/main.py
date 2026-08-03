"""ReceiptMind FastAPI application entrypoint.

Run with: uv run uvicorn backend.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import receipts, search, stats, upload
from backend.config import get_settings
from backend.database.init_db import init_db
from backend.utils.exceptions import ReceiptMindError
from backend.utils.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    init_db()
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title="ReceiptMind API",
    description="AI receipt OCR + semantic search over your purchase history.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ReceiptMindError)
async def receiptmind_error_handler(_request: Request, exc: ReceiptMindError) -> JSONResponse:
    logger.warning("%s: %s", exc.error_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message, "error_code": exc.error_code}
    )


app.include_router(upload.router)
app.include_router(receipts.router)
app.include_router(search.router)
app.include_router(stats.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


# Serve uploaded receipt images (used by the frontend's receipt image viewer).
import os  # noqa: E402

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=settings.upload_dir), name="images")
