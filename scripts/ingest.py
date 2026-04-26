import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import logging
from app.core.config import settings
from app.data.preprocess.chunking import chunk_text
from app.llm.embeddings import embed_text
from app.db.models import Chunk, Document, IngestionRun
from app.db.session import SessionLocal
from app.vectorstore.qdrant_client import upsert_points

logger = logging.getLogger(__name__)


def parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fetch_external_market_data() -> list:
    fetched_docs = []

    try:
        fed_reg_url = "https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=securities-and-exchange-commission&per_page=5"
        response = requests.get(fed_reg_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("results", []):
                fetched_docs.append(
                    {
                        "source_name": "Federal Register",
                        "source_url": item.get("html_url"),
                        "title": item.get("title"),
                        "lane": "regulation",
                        "raw_text": item.get("abstract")
                        or item.get("body", "No content available."),
                        "published_at": item.get("publication_date"),
                    }
                )
            logger.info(
                f"Successfully fetched {len(data.get('results', []))} regulatory documents from Federal Register."
            )
    except Exception as e:
        logger.error(f"Failed to fetch regulatory data: {e}")

    try:
        fred_api_key = getattr(settings, "FRED_API_KEY", None)
        if fred_api_key:
            series_map = {
                "GDP": "Gross Domestic Product (GDP)",
                "CPIAUCSL": "Consumer Price Index (Inflation)",
                "FEDFUNDS": "Effective Federal Funds Rate",
                "UNRATE": "Unemployment Rate",
            }
            for series_id, series_name in series_map.items():
                fred_url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={fred_api_key}&file_type=json&limit=1&sort_order=desc"
                resp = requests.get(fred_url, timeout=10)
                if resp.status_code == 200:
                    obs = resp.json().get("observations", [])
                    if obs:
                        latest = obs[0]
                        fetched_docs.append(
                            {
                                "source_name": "FRED",
                                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                                "title": f"Macroeconomic Indicator: {series_name} - {latest['date']}",
                                "lane": "macro",
                                "raw_text": f"The latest value for {series_name} ({series_id}) is {latest['value']} as of {latest['date']}.",
                                "published_at": latest["date"],
                            }
                        )
            logger.info(f"Successfully fetched {len(series_map)} series from FRED.")
        else:
            logger.warning("FRED_API_KEY not found in settings. Skipping macro fetch.")
    except Exception as e:
        logger.error(f"Failed to fetch FRED data: {e}")

    try:
        tickers = ["AAPL.US", "MSFT.US", "SPY.US", "QQQ.US", "DIA.US"]
        for ticker in tickers:
            stooq_url = f"https://stooq.com/q/l/?s={ticker}&f=sd2t2ohlcv&h&e=json"
            resp = requests.get(stooq_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                symbols = data.get("symbols", [])
                if symbols:
                    s = symbols[0]
                    fetched_docs.append(
                        {
                            "source_name": "Stooq",
                            "source_url": f"https://stooq.com/q/?s={ticker}",
                            "title": f"Market Quote: {ticker} - {s.get('date')}",
                            "lane": "stocks",
                            "raw_text": (
                                f"Market data for {ticker}. "
                                f"Open: {s.get('open')}, High: {s.get('high')}, "
                                f"Low: {s.get('low')}, Close: {s.get('close')}, "
                                f"Volume: {s.get('volume')} as of {s.get('date')} {s.get('time')}."
                            ),
                            "published_at": (
                                f"{s.get('date')}T{s.get('time')}"
                                if s.get("date")
                                else None
                            ),
                        }
                    )
        logger.info(f"Successfully fetched {len(tickers)} stock quotes from Stooq.")
    except Exception as e:
        logger.error(f"Failed to fetch stock data: {e}")

    return fetched_docs


def main() -> None:
    records = []
    project_root = Path(__file__).resolve().parents[1]
    input_file = project_root / "data" / "raw" / "seed_market_docs.json"
    source_info = ""

    if input_file.exists():
        with input_file.open("r", encoding="utf-8") as f:
            records = json.load(f)
        source_info = "Seed File"
        logger.info(f"Loaded {len(records)} records from seed file: {input_file}")
    else:
        logger.warning(f"Seed file not found at {input_file}.")

    try:
        live_records = fetch_external_market_data()
        if live_records:
            records.extend(live_records)
            source_info = (
                f"{source_info} + Live API Feed" if source_info else "Live API Feed"
            )
            logger.info(f"Fetched {len(live_records)} live records.")
        else:
            logger.warning("Live fetch returned no records. No data to ingest.")
    except Exception as e:
        logger.error(f"Error during ingestion process: {e}")

    if not records:
        logger.error("No records found for ingestion. Exiting.")
        return

    db = SessionLocal()
    run = IngestionRun(
        lane="mixed",
        status="running",
        source_count=len(records),
        chunk_count=0,
        details={"source_origin": source_info},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    total_chunks = 0
    qdrant_points = []

    try:
        for row in records:
            raw_title = row.get("title", "untitled")
            truncated_title = raw_title[:255]

            existing = (
                db.query(Document)
                .filter(
                    Document.title == truncated_title,
                    Document.lane == row.get("lane", "macro"),
                )
                .first()
            )
            if existing:
                logger.info(f"Skipping existing document: {row.get('title')}")
                continue

            doc = Document(
                source_name=row.get("source_name", "unknown")[:255],
                source_url=(
                    row.get("source_url")[:255] if row.get("source_url") else None
                ),
                title=truncated_title,
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

        if qdrant_points:
            upsert_points(qdrant_points)
        run.status = "completed"
        run.chunk_count = total_chunks
        db.commit()
        logger.info(
            f"Ingestion complete. documents={len(records)} chunks={total_chunks}"
        )

    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        db.rollback()
        run.status = "failed"
        run.details = {"error": str(exc)}
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
