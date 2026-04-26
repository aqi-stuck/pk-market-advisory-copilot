import logging
import httpx
from fastapi import APIRouter
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
async def health_check():
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

        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{qdrant_url}/healthz", headers=headers)
            if response.status_code != 200:
                vectorstore_status = "error"
                error_details["vectorstore"] = f"Qdrant status {response.status_code}"
    except Exception as e:
        vectorstore_status = "error"
        error_details["vectorstore"] = f"Check failed: {str(e)}"
        logger.warning(f"Health check: Vectorstore connectivity issue: {e}")

    details = {
        "database": db_status,
        "vectorstore": vectorstore_status,
        "errors": error_details if error_details else None,
    }

    status = "ok" if db_status == "ok" and vectorstore_status == "ok" else "degraded"

    return HealthResponse(status=status, version=settings.VERSION, details=details)
