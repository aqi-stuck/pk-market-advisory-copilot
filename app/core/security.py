from fastapi import Security, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings


security = HTTPBearer()


def get_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the API key from the Authorization header
    """
    if not settings.API_KEY:
        # If no API key is set in config, allow all requests (development mode)
        return credentials.credentials

    if credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials