from typing import Optional
from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception class for the application"""
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.code = code


class DataNotFoundError(BaseAppException):
    """Raised when requested data is not found"""
    pass


class ValidationError(BaseAppException):
    """Raised when data validation fails"""
    pass


class DatabaseConnectionError(BaseAppException):
    """Raised when there's an issue connecting to the database"""
    pass


class VectorDatabaseError(BaseAppException):
    """Raised when there's an issue with the vector database"""
    pass


class APIKeyMissingError(HTTPException):
    """Raised when API key is required but not provided"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )


class QueryProcessingError(BaseAppException):
    """Raised when there's an error processing a query"""
    pass