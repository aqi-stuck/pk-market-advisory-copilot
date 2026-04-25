from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import requests

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    details: Optional[dict] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service availability.
    Now uses a singleton-style engine check to avoid overhead.
    """
    db_status = "ok"
    vectorstore_status = "ok"
    error_details = {}

    try:
        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        error_details["database"] = "Could not connect to PostgreSQL"
        db_status = "error"

    try:
        qdrant_url = settings.QDRANT_URL.rstrip("/")
        if not qdrant_url.startswith("http"):
            # Default to https for cloud endpoints (e.g., .qdrant.io)
            protocol = "https" if ".qdrant.io" in qdrant_url else "http"
            qdrant_url = f"{protocol}://{qdrant_url}"

        headers = {}
        if settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY

        response = requests.get(f"{qdrant_url}/health", headers=headers, timeout=3)
        if response.status_code != 200:
            vectorstore_status = "error"
            error_details["vectorstore"] = (
                f"Qdrant returned status {response.status_code}"
            )
    except requests.RequestException as e:
        error_details["vectorstore"] = str(e)
        vectorstore_status = "error"

    details = {
        "database": db_status,
        "vectorstore": vectorstore_status,
        "errors": error_details if error_details else None,
    }

    status = "ok" if db_status == "ok" and vectorstore_status == "ok" else "degraded"

    return HealthResponse(status=status, version=settings.VERSION, details=details)
