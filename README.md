# US Market Advisory RAG System

A production-grade Retrieval-Augmented Generation (RAG) API that answers natural language questions about US financial markets — equities, macroeconomic indicators, and financial regulations — grounded in real source documents with full citations.

Built with FastAPI, Qdrant, PostgreSQL, and Azure OpenAI.

---

## What It Does

Ask questions like:

- *"What is the current outlook for US equity markets?"*
- *"How has CPI trended over the last quarter?"*
- *"What are the latest SEC disclosure requirements?"*

The system retrieves the most relevant document chunks from a vector store, reranks them for precision, generates a grounded answer using GPT-4o, and returns source citations. You can interact via a standard REST API or the dedicated Streamlit UI.

---

## Architecture

```
POST /v1/query
      │
      ▼
 Guardrails ──── rejects off-topic or injection attempts
      │
      ▼
  Retriever ──── embeds query (Azure text-embedding-3-small)
                 searches Qdrant vector store (cosine similarity)
      │
      ▼
  Reranker ──── scores each chunk for relevance via GPT-4o
                selects top-k most relevant passages
      │
      ▼
  Generator ─── builds grounded prompt with context
                calls GPT-4o for final answer
      │
      ▼
  Response ──── answer + citations + metadata logged to Postgres
```

### Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Vector Store | Qdrant |
| Embeddings | Azure OpenAI `text-embedding-3-small` (1536-dim) |
| LLM | Azure OpenAI `gpt-4o` |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Containerization | Docker + Docker Compose |
| Logging | Structured JSON logging |
| CI | GitHub Actions |

### Data Lanes

| Lane | Sources |
|---|---|
| `stocks` | Stooq US market data, S&P 500 / ETF price series |
| `macro` | FRED — CPI, GDP, interest rates, labor indicators |
| `regulation` | SEC / Federal Register — filings, rule updates, disclosures |

---

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── routes_health.py       # GET /health
│   │   ├── routes_ingest.py       # POST /v1/ingest
│   │   ├── routes_query.py        # POST /v1/query
│   │   └── schemas.py
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── logging.py             # Structured JSON logging
│   │   └── security.py            # Bearer token auth
│   ├── data/preprocess/
│   │   └── chunking.py            # Sliding window chunker
│   ├── db/
│   │   ├── models.py              # Document, Chunk, QueryLog, IngestionRun
│   │   └── session.py
│   ├── llm/
│   │   └── embeddings.py          # Azure OpenAI embed_text()
│   ├── rag/
│   │   ├── pipeline.py            # Full RAG orchestration
│   │   ├── retriever.py           # Vector search
│   │   ├── reranker.py            # LLM-based reranking
│   │   └── guardrails.py          # Scope + injection checks
│   └── vectorstore/
│       └── qdrant_client.py
├── alembic/                       # Database migrations
├── scripts/
│   └── ingest.py                  # Seed data ingestion script
├── tests/                         # Pytest test suite
├── data/raw/                      # Seed market documents
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An Azure OpenAI resource with:
  - `text-embedding-3-small` deployment
  - `gpt-4o` deployment

### 1. Clone and configure

```bash
git clone <repo-url>
cd us-market-advisory-copilot
cp .env.example .env
# Fill in your Azure OpenAI credentials in .env
```

### 2. Start services

```bash
docker-compose up -d --build
```

### 3. Run initial ingestion

```bash
docker-compose exec api bash -c "PYTHONPATH=/app python3 scripts/ingest.py"
```

### 4. Query the API

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"query": "What is the outlook for US equity markets?", "top_k": 5}'
```

---

## API Reference

### `GET /health`

Returns system health including database and vector store connectivity.

### `POST /v1/query`

```json
{
  "query": "string",
  "lane_hint": "stocks | macro | regulation (optional)",
  "top_k": 8,
  "include_citations": true
}
```

Response:
```json
{
  "answer": "string",
  "citations": [
    {
      "source_title": "string",
      "source_url": "string",
      "chunk_id": "string",
      "quote": "string"
    }
  ],
  "metadata": {
    "retrieval_k": 8,
    "reranked_k": 3,
    "latency_ms": 1240.5,
    "query_log_id": 42
  }
}
```

### `POST /v1/ingest`

Protected endpoint for ingesting new documents.

```json
{
  "lane": "stocks | macro | regulation",
  "documents": [
    {
      "source_name": "string",
      "title": "string",
      "raw_text": "string"
    }
  ]
}
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `AZURE_CHAT_DEPLOYMENT` | Chat model deployment name |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant vector store URL |
| `API_KEY` | Bearer token for API authentication |

---

## Database Schema

| Table | Purpose |
|---|---|
| `documents` | Raw ingested documents with metadata |
| `chunks` | Text chunks with Qdrant point IDs |
| `ingestion_runs` | Audit log of ingestion jobs |
| `query_logs` | Every query with answer, latency, retrieval stats |

Migrations managed with Alembic:
```bash
docker-compose exec api bash -c "cd /app && alembic upgrade head"
```

---

## Running Tests

```bash
docker-compose exec api bash -c "cd /app && python -m pytest tests/ -v"
```

---

## CI/CD

GitHub Actions runs the full test suite on every push to `main` and `develop`, and on all pull requests. See `.github/workflows/ci.yml`.

Add these secrets to your GitHub repository:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
