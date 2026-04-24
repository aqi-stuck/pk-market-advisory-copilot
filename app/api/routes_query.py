import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import QueryRequest, QueryResponse
from app.core.security import get_api_key
from app.db.models import QueryLog
from app.db.session import get_db
from app.rag.retriever import retrieve_chunks

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    retrieved = retrieve_chunks(
        query=request.query, top_k=request.top_k or 8, lane_hint=request.lane_hint
    )
    if not retrieved:
        answer = "No relevant market context was found for your query."
    else:
        parts = [r.get("chunk_text", "").strip() for r in retrieved[:2]]
        parts = [part for part in parts if part]
        answer = "\n\n".join(parts)

    retrieved_k = len(retrieved)
    if request.include_citations:
        citations = [
            {
                "source_title": item.get("title") or "Unknown source",
                "source_url": item.get("source_url") or "",
                "chunk_id": str(item.get("chunk_id") or ""),
                "quote": (item.get("chunk_text") or "")[:280],
            }
            for item in retrieved
        ]
    else:
        citations = []

    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    log = QueryLog(
        question=request.query,
        answer=answer,
        lane_hint=request.lane_hint,
        retrieval_k=retrieved_k,
        reranked_k=0,
        latency_ms=latency_ms,
        extra_metadata={"stage": "retrieval_mvp"},
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return QueryResponse(
        answer=answer,
        citations=citations,
        metadata={
            "retrieval_k": retrieved_k,
            "reranked_k": 0,
            "latency_ms": latency_ms,
            "query_log_id": log.id,
        },
    )
