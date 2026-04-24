from openai import AzureOpenAI
from app.core.config import settings

def embed_text(text: str) -> list[float]:
    client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )
    response = client.embeddings.create(input=text, model=settings.AZURE_EMBEDDING_DEPLOYMENT)
    return response.data[0].embedding
