from mcp.server.fastmcp import FastMCP
from app.rag.pipeline import run_pipeline
from app.core.config import settings
from app.db.session import SessionLocal
from app.api.routes_ingest import ingest_endpoint
from app.api.schemas import IngestRequest
from typing import Optional

# Initialize FastMCP server
mcp = FastMCP("US-Market-Advisory")


@mcp.tool()
def ask_market_expert(query: str, lane: Optional[str] = None) -> str:
    """
    Consult the US Market Advisory RAG system.
    Use this for questions about US equities, macroeconomics (CPI, GDP, Fed rates),
    or SEC financial regulations.

    Args:
        query: The financial or regulatory question.
        lane: Optional hint ('stocks', 'macro', or 'regulation').
    """
    # We use the existing pipeline logic
    answer, chunks, ret_k, rer_k = run_pipeline(
        query=query, lane_hint=lane, top_k=5, rerank_k=3
    )

    # Format the response for the LLM
    if not chunks:
        return answer

    formatted_response = f"Expert Analysis:\n{answer}\n\nSources used:\n"
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title", "Unknown Source")
        formatted_response += f"[{i}] {title}\n"

    return formatted_response


@mcp.tool()
async def ingest_market_data(title: str, text: str, lane: str = "macro") -> str:
    """
    Ingest new market data into the RAG system immediately.
    Use this when you have new information that should be saved for future queries.

    Args:
        title: The title of the document.
        text: The full text content to be chunked and embedded.
        lane: The category ('stocks', 'macro', or 'regulation').
    """
    db = SessionLocal()
    try:
        request = IngestRequest(
            lane=lane,
            documents=[{"title": title, "raw_text": text, "source_name": "MCP User"}],
        )
        # We reuse the logic from the API endpoint
        result = await ingest_endpoint(request=request, db=db, api_key=settings.API_KEY)
        return f"Successfully ingested document. Run ID: {result.details.get('ingestion_run_id')}"
    except Exception as e:
        return f"Ingestion failed: {str(e)}"
    finally:
        db.close()


@mcp.resource("market://status")
def get_system_status() -> str:
    """Provides the current health status of the advisory system dependencies."""
    # This could be expanded to call your health check logic
    return (
        f"System: {settings.PROJECT_NAME}, Version: {settings.VERSION}, Status: Online"
    )


if __name__ == "__main__":
    # Running this script directly starts the MCP server over stdio
    # This is how Claude Desktop or other clients connect to it.
    mcp.run()
