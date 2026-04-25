from app.core.config import settings
from app.llm.clients import get_embedding_client


def embed_text(text: str) -> list[float]:
    client = get_embedding_client()

    response = client.embeddings.create(
        input=text, model=settings.AZURE_EMBEDDING_DEPLOYMENT
    )
    return response.data[0].embedding
