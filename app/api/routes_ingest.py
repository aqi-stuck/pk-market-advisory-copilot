from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import IngestRequest, IngestResponse
from app.core.security import get_api_key
from app.db.models import Document, IngestionRun
from app.db.session import get_db
import uuid
from app.data.preprocess.chunking import chunk_text
from app.llm.embeddings import embed_text
from app.vectorstore.qdrant_client import upsert_points
from app.core.config import settings
from app.db.models import Chunk

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(
    request: IngestRequest,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    source_count = len(request.source_urls or [])
    document_count = len(request.documents or [])

    run = IngestionRun(
        lane=request.lane,
        status="running",
        source_count=source_count,
        chunk_count=0,
        details={"mode": "api_mvp", "documents_received": document_count},
    )
    db.add(run)
    db.flush()

    docs = []
    for item in request.documents or []:
        # Basic duplicate check by title and lane
        existing = (
            db.query(Document)
            .filter(Document.title == item.get("title"), Document.lane == request.lane)
            .first()
        )
        if existing:
            continue

        doc = Document(
            lane=request.lane,
            source_name=item.get("source_name"),
            title=item.get("title"),
            raw_text=item.get("raw_text"),
            extra_metadata={"ingestion_run_id": run.id},
        )
        db.add(doc)
        docs.append(doc)
    db.flush()
    points = []
    for doc in docs:
        for i, chunk_str in enumerate(
            chunk_text(doc.raw_text or "", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        ):
            point_id = str(uuid.uuid4())
            vector = embed_text(chunk_str)
            db.add(
                Chunk(
                    document_id=doc.id,
                    chunk_index=i,
                    chunk_text=chunk_str,
                    qdrant_point_id=point_id,
                    embedding_model=settings.AZURE_EMBEDDING_DEPLOYMENT,
                )
            )
            points.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "text": chunk_str,
                        "document_id": doc.id,
                        "lane": doc.lane,
                    },
                }
            )
    upsert_points(points)
    run.chunk_count = len(points)
    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)

    return IngestResponse(
        status=run.status,
        documents_processed=document_count,
        details={
            "ingestion_run_id": run.id,
            "lane": run.lane,
            "source_count": source_count,
        },
    )
