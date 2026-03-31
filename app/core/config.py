from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pakistan Market Advisory RAG System"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "A RAG system for providing insights on Pakistani financial markets"

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/market_advisory_db"

    # Qdrant settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None

    # API settings
    API_V1_STR: str = "/v1"
    DEBUG: bool = False

    # Security
    API_KEY: Optional[str] = None

    # Data processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    class Config:
        env_file = ".env"


settings = Settings()