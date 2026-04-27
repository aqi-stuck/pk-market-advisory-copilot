import logging
import httpx
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from sqlalchemy import text
from app.db.session import SessionLocal
from app.vectorstore.qdrant_client import QDRANT_COLLECTION, get_qdrant_client

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    details: Optional[dict] = None


@router.get("/health/debug")
async def health_debug():
    db = SessionLocal()
    payload = {
        "status": "ok",
        "version": settings.VERSION,
        "database": {},
        "vectorstore": {},
        "ingestion": {},
        "errors": {},
    }

    try:
        payload["database"]["documents"] = db.execute(
            text("SELECT COUNT(1) FROM documents")
        ).scalar_one()
        payload["database"]["chunks"] = db.execute(
            text("SELECT COUNT(1) FROM chunks")
        ).scalar_one()
        payload["database"]["query_logs"] = db.execute(
            text("SELECT COUNT(1) FROM query_logs")
        ).scalar_one()

        # Read ingestion_runs in a schema-tolerant way so older DBs do not break this endpoint.
        available_columns = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ingestion_runs'
                """
            )
        ).fetchall()
        column_names = {row[0] for row in available_columns}

        base_cols = ["id", "lane", "started_at", "finished_at"]
        optional_cols = ["status", "source_count", "chunk_count", "details"]
        selected = [c for c in base_cols + optional_cols if c in column_names]

        if selected:
            query = text(
                f"SELECT {', '.join(selected)} FROM ingestion_runs ORDER BY started_at DESC LIMIT 1"
            )
            latest_run = db.execute(query).mappings().first()
            if latest_run:
                latest_payload = dict(latest_run)
                for dt_col in ["started_at", "finished_at"]:
                    value = latest_payload.get(dt_col)
                    if value is not None and hasattr(value, "isoformat"):
                        latest_payload[dt_col] = value.isoformat()
                payload["ingestion"]["latest"] = latest_payload
            else:
                payload["ingestion"]["latest"] = None
        else:
            payload["ingestion"]["latest"] = None
    except Exception as exc:
        payload["status"] = "degraded"
        payload["errors"]["database"] = str(exc)

    try:
        client = get_qdrant_client()
        exists = client.collection_exists(QDRANT_COLLECTION)
        payload["vectorstore"]["collection_exists"] = exists
        if exists:
            info = client.get_collection(QDRANT_COLLECTION)
            payload["vectorstore"]["collection"] = QDRANT_COLLECTION
            payload["vectorstore"]["points_count"] = info.points_count
            payload["vectorstore"]["indexed_vectors_count"] = info.indexed_vectors_count
    except Exception as exc:
        payload["status"] = "degraded"
        payload["errors"]["vectorstore"] = str(exc)

    if not payload["errors"]:
        payload["errors"] = None

    db.close()
    return payload


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
