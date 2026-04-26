import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings

logger = logging.getLogger(__name__)
QDRANT_COLLECTION = "market_chunks"


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.QDRANT_URL.strip(), api_key=settings.QDRANT_API_KEY
    )


def ensure_collection(vector_size: int = 1536) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections

    if any(collection.name == QDRANT_COLLECTION for collection in collections):
        return

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def upsert_points(points: List[Dict[str, Any]]) -> None:
    if not points:
        return

    ensure_collection(vector_size=len(points[0]["vector"]))
    client = get_qdrant_client()

    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            models.PointStruct(
                id=point["id"],
                vector=point["vector"],
                payload=point["payload"],
            )
            for point in points
        ],
    )


def search_similar(vector: List[float], limit: int = 5):
    ensure_collection(vector_size=len(vector))
    client = get_qdrant_client()

    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        limit=limit,
    )
    return results.points
