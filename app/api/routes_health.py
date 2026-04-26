import logging
import httpx
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    details: Optional[dict] = None


@router.get("/health", response_model=HealthResponse)
async def health_check(response: Response):
    db_status = "ok"
    vectorstore_status = "ok"
    error_details = {}

    try:
        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
        error_details["database"] = f"Connection failed: {str(e)}"
        db_status = "error"

    try:
        qdrant_url = settings.QDRANT_URL.strip().rstrip("/")
        headers = {}
        if settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            q_resp = await client.get(f"{qdrant_url}/healthz", headers=headers)
            if q_resp.status_code != 200:
                vectorstore_status = "error"
                error_details["vectorstore"] = f"Qdrant status {q_resp.status_code}"
    except Exception as e:
        vectorstore_status = "error"
        error_details["vectorstore"] = f"Check failed: {str(e)}"
        logger.warning(f"Health check: Vectorstore not ready or unreachable: {e}")

    details = {
        "database": db_status,
        "vectorstore": vectorstore_status,
        "errors": error_details if error_details else None,
    }

    status_val = (
        "ok" if db_status == "ok" and vectorstore_status == "ok" else "degraded"
    )
    if status_val == "degraded":
        logger.warning(f"System health degraded: {error_details}")

    return HealthResponse(status=status_val, version=settings.VERSION, details=details)
