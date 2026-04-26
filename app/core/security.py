import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer(auto_error=False)


def get_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """
    If API_KEY is unset, allow requests only in development mode.
    If API_KEY is set, require matching Bearer token.
    """
    environment = str(getattr(settings, "ENVIRONMENT", "")).lower()

    if not settings.API_KEY:
        if environment == "development":
            return credentials.credentials if credentials else "dev-mode"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not credentials or not secrets.compare_digest(
        credentials.credentials, settings.API_KEY
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
