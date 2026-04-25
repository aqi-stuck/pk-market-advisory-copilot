from typing import Any, Dict, List

from app.core.config import settings
from app.llm.clients import get_chat_client


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Reranks retrieved chunks by asking the LLM to score each one for
    relevance to the query. Returns top_k most relevant chunks.
    Falls back to original order if reranking fails.
    """
    if not chunks:
        return chunks

    scored = []
    client = get_chat_client()
    try:
        # If client initialization fails, it will be caught here
        pass
    except Exception:
        return chunks  # Fallback to original order if client fails

    for chunk in chunks:
        text = (chunk.get("chunk_text") or "").strip()
        if not text:
            scored.append((0.0, chunk))
            continue
        try:
            response = client.chat.completions.create(
                model=settings.CHAT_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a relevance scorer. Given a query and a passage, "
                            "respond with a single float between 0.0 and 1.0 indicating "
                            "how relevant the passage is to the query. Nothing else."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\n\nPassage: {text[:500]}",
                    },
                ],
                max_tokens=5,
                temperature=0,
            )
            score = float(response.choices[0].message.content.strip())
        except Exception:
            score = chunk.get("score", 0.0)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]
