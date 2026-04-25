from openai import OpenAI, AzureOpenAI
from app.core.config import settings


def get_chat_client() -> OpenAI:
    """
    Initializes the OpenAI client for chat models (e.g., GitHub Models).
    """
    return OpenAI(
        base_url=settings.GITHUB_MODELS_BASE_URL,
        api_key=settings.GITHUB_TOKEN,
    )


def get_embedding_client() -> AzureOpenAI:
    """
    Initializes the Azure OpenAI client for embedding models.
    """
    # Ensure Azure-specific settings are present for AzureOpenAI
    if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
        raise ValueError(
            "Azure OpenAI endpoint and API key must be configured for embedding client."
        )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )
