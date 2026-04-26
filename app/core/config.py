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
    GITHUB_MODELS_BASE_URL: str = (
        "https://models.inference.ai.azure.com"  # Endpoint for GitHub Models
    )
    EMBEDDING_DIMENSIONS: int = 1536
    GITHUB_CHAT_MODEL_NAME: str = (
        "gpt-4o-mini"  # Model name for chat (from GitHub Models)
    )
    GITHUB_TOKEN: Optional[str] = None
    FRED_API_KEY: Optional[str] = None

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/market_advisory_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_prefix(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # Qdrant settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None

    # API settings
    API_V1_STR: str = "/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Security
    API_KEY: Optional[str] = None

    # Data processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
