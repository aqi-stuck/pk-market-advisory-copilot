from typing import Any, Dict, List, Optional

from app.llm.embeddings import embed_text
from app.vectorstore.qdrant_client import search_similar


def retrieve_chunks(
    query: str, top_k: int = 5, lane_hint: Optional[str] = None
) -> List[Dict[str, Any]]:
    vector = embed_text(query)
    hits = search_similar(vector, limit=top_k)

    results: List[Dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        if lane_hint and payload.get("lane") != lane_hint:
            continue

        results.append(
            {
                "score": hit.score,
                "chunk_id": str(hit.id),
                "document_id": payload.get("document_id"),
                "chunk_index": payload.get("chunk_index"),
                "title": payload.get("title"),
                "source_name": payload.get("source_name"),
                "source_url": payload.get("source_url"),
                "chunk_text": payload.get("chunk_text"),
                "lane": payload.get("lane"),
            }
        )

    return results
