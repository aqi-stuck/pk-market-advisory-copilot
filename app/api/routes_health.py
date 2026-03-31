from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
import asyncio

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    details: Optional[dict] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service availability
    """
    # In a real implementation, you would check database connections,
    # external service availability, etc.
    details = {
        "database": "ok",  # Would check actual DB connection
        "vectorstore": "ok",  # Would check actual vector store connection
        "external_apis": "ok"  # Would check external API availability
    }

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        details=details
    )