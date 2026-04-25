from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.rag.guardrails import check_query
from app.rag.reranker import rerank_chunks
from app.rag.retriever import retrieve_chunks
from app.llm.clients import get_chat_client

SYSTEM_PROMPT = """You are a professional US financial markets analyst assistant.
Answer the user's question using ONLY the provided market context below.
Be concise, factual, and cite specific data points when available.
If the context does not contain enough information, say so clearly.
Do not speculate beyond what the context supports."""


def run_pipeline(
    query: str,
    top_k: int = 8,
    rerank_k: int = 3,
    lane_hint: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], int, int]:
    """
    Full RAG pipeline: guardrails → retrieve → rerank → generate.
    Returns (answer, chunks, retrieved_k, reranked_k).
    """
    # 1. Guardrails
    refusal = check_query(query)
    if refusal:
        return refusal, [], 0, 0

    # 2. Retrieve
    chunks = retrieve_chunks(query=query, top_k=top_k, lane_hint=lane_hint)
    retrieved_k = len(chunks)
    try:
        chunks = retrieve_chunks(query=query, top_k=top_k, lane_hint=lane_hint)
        retrieved_k = len(chunks)
        if not chunks:
            return "No relevant market context was found for your query.", [], 0, 0
    except Exception as e:
        return f"Retrieval failed: {str(e)}", [], 0, 0

    if not chunks:
        return "No relevant market context was found for your query.", [], 0, 0

    # 3. Rerank
    reranked = rerank_chunks(query=query, chunks=chunks, top_k=rerank_k)
    reranked_k = len(reranked)
    try:
        reranked = rerank_chunks(query=query, chunks=chunks, top_k=rerank_k)
        reranked_k = len(reranked)
    except Exception as e:
        # Fallback to original chunks if reranking crashes unexpectedly
        reranked = chunks[:rerank_k]
        reranked_k = len(reranked)

    # 4. Build context
    context_parts = []
    for i, chunk in enumerate(reranked, 1):
        title = chunk.get("title") or "Unknown"
        text = (chunk.get("chunk_text") or "").strip()
        context_parts.append(f"[{i}] {title}\n{text}")
    context = "\n\n".join(context_parts)

    # 5. Generate answer
    try:
        client = get_chat_client()
        response = client.chat.completions.create(
            model=settings.GITHUB_CHAT_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}",
                },
            ],
            max_tokens=512,
            temperature=0.2,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Answer generation failed: {str(e)}"

    return answer, reranked, retrieved_k, reranked_k
