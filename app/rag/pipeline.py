import re
from typing import Any, Dict, List, Optional, Tuple

from openai import RateLimitError

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


def _extract_retry_seconds(message: str) -> Optional[int]:
    match = re.search(r"wait\s+(\d+)\s+seconds", message, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _is_rate_limit_error(err: Exception) -> bool:
    status_code = getattr(err, "status_code", None)
    if status_code == 429:
        return True

    msg = str(err).lower()
    return "rate limit" in msg or "ratelimit" in msg or "error code: 429" in msg


def _is_connection_error(err: Exception) -> bool:
    status_code = getattr(err, "status_code", None)
    if status_code is not None:
        return False

    msg = str(err).lower()
    error_type = err.__class__.__name__.lower()
    return (
        "connection error" in msg
        or "timed out" in msg
        or "timeout" in msg
        or "apiconnectionerror" in error_type
        or "apitimeouterror" in error_type
    )


def _build_model_candidates() -> List[str]:
    candidates = [settings.GITHUB_CHAT_MODEL_NAME]
    raw_fallbacks = settings.GITHUB_CHAT_FALLBACK_MODELS or ""
    for model_name in [m.strip() for m in raw_fallbacks.split(",") if m.strip()]:
        if model_name not in candidates:
            candidates.append(model_name)
    return candidates


def _format_retry_hint(retry_seconds: Optional[int]) -> str:
    if retry_seconds is None:
        return "Please retry later or switch to another configured model."

    hours = retry_seconds // 3600
    minutes = (retry_seconds % 3600) // 60
    if hours > 0:
        return f"Please retry in about {hours}h {minutes}m, or switch to another configured model."
    if minutes > 0:
        return (
            f"Please retry in about {minutes}m, or switch to another configured model."
        )
    return f"Please retry in about {retry_seconds}s, or switch to another configured model."


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
    try:
        chunks = retrieve_chunks(query=query, top_k=top_k, lane_hint=lane_hint)
        retrieved_k = len(chunks)
        if not chunks:
            return "No relevant market context was found for your query.", [], 0, 0
    except Exception as e:
        return f"Retrieval failed: {str(e)}", [], 0, 0

    # 3. Rerank
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
        model_candidates = _build_model_candidates()
        rate_limit_error: Optional[Exception] = None
        connection_error: Optional[Exception] = None

        for model_name in model_candidates:
            try:
                response = client.chat.completions.create(
                    model=model_name,
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
                return answer, reranked, retrieved_k, reranked_k
            except RateLimitError as e:
                rate_limit_error = e
                continue
            except Exception as e:
                if _is_rate_limit_error(e):
                    rate_limit_error = e
                    continue
                if _is_connection_error(e):
                    connection_error = e
                    continue
                raise

        if rate_limit_error is not None:
            retry_seconds = _extract_retry_seconds(str(rate_limit_error))
            answer = (
                "Answer generation is temporarily unavailable due to model rate limits. "
                + _format_retry_hint(retry_seconds)
            )
        elif connection_error is not None:
            answer = (
                "Answer generation is temporarily unavailable due to an upstream model connection issue. "
                "Please retry in a minute."
            )
        else:
            answer = "Answer generation failed unexpectedly."
    except Exception as e:
        answer = f"Answer generation failed: {str(e)}"

    return answer, reranked, retrieved_k, reranked_k
