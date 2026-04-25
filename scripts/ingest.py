import json
import requests
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.data.preprocess.chunking import chunk_text
from app.llm.embeddings import embed_text
from app.db.models import Chunk, Document, IngestionRun
from app.db.session import SessionLocal
from app.vectorstore.qdrant_client import upsert_points


def parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fetch_external_market_data() -> list:
    """
    Example function to fetch live data.
    In production, you would replace this with calls to FRED, SEC EDGAR, or News APIs.
    """
    # For demonstration, we'll return a sample structure.
    # You could use requests.get("https://api.example.com/finance").json()
    return [
        {
            "source_name": "Live Feed",
            "title": f"Market Update - {datetime.now().strftime('%Y-%m-%d')}",
            "lane": "macro",
            "raw_text": "The latest macroeconomic data indicates a stabilizing trend in inflation...",
            "published_at": datetime.utcnow().isoformat(),
        }
    ]


def main() -> None:
    # Logic: If running in production (Cron), try fetching live data.
    # Otherwise, fallback to the seed file.
    records = []
    try:
        records = fetch_external_market_data()
        print(f"Fetched {len(records)} live records.")
    except Exception as e:
        print(f"Live fetch failed, falling back to seed file: {e}")
        project_root = Path(__file__).resolve().parents[1]
        input_file = project_root / "data" / "raw" / "seed_market_docs.json"
        if input_file.exists():
            with input_file.open("r", encoding="utf-8") as f:
                records = json.load(f)

    db = SessionLocal()
    run = IngestionRun(
        lane="mixed",
        status="running",
        source_count=len(records),
        chunk_count=0,
        details={"source_file": str(input_file)},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    total_chunks = 0
    qdrant_points = []

    try:
        for row in records:
            doc = Document(
                source_name=row.get("source_name", "unknown"),
                source_url=row.get("source_url"),
                title=row.get("title", "untitled"),
                lane=row.get("lane", "macro"),
                published_at=parse_datetime(row.get("published_at")),
                raw_text=row.get("raw_text", ""),
                extra_metadata={"ingestion_run_id": run.id},
            )
            db.add(doc)
            db.flush()

            chunks = chunk_text(
                doc.raw_text or "",
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )

            for idx, text_part in enumerate(chunks):
                point_id = str(uuid4())
                vector = embed_text(text_part)

                db.add(
                    Chunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        chunk_text=text_part,
                        qdrant_point_id=point_id,
                        embedding_model=settings.AZURE_EMBEDDING_DEPLOYMENT,
                        extra_metadata={"lane": doc.lane},
                    )
                )

                qdrant_points.append(
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {
                            "document_id": doc.id,
                            "chunk_index": idx,
                            "lane": doc.lane,
                            "title": doc.title,
                            "source_name": doc.source_name,
                            "source_url": doc.source_url,
                            "chunk_text": text_part,
                        },
                    }
                )

            total_chunks += len(chunks)

        upsert_points(qdrant_points)
        run.status = "completed"
        run.chunk_count = total_chunks
        db.commit()
        print(f"Ingestion complete. documents={len(records)} chunks={total_chunks}")

    except Exception as exc:
        run.status = "failed"
        run.details = {"error": str(exc)}
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
