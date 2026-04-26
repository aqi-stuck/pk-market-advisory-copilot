from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from typing import Any, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "US Market Advisory RAG System"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "A RAG system for providing insights on US financial markets"
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"
    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    GITHUB_MODELS_BASE_URL: str = "https://models.inference.ai.azure.com"
    EMBEDDING_DIMENSIONS: int = 1536
    GITHUB_CHAT_MODEL_NAME: str = "gpt-4o-mini"
    GITHUB_TOKEN: Optional[str] = None
    DATABASE_URL: str = "postgresql://user:password@postgres:5432/market_advisory_db"
    FRED_API_KEY: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        return v.strip() if isinstance(v, str) else v

    @field_validator("QDRANT_URL", mode="before")
    @classmethod
    def clean_qdrant_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().rstrip("/")
        return v

    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: Optional[str] = None
    API_V1_STR: str = "/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    API_KEY: Optional[str] = None
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
