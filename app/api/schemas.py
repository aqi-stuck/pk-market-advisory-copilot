from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TimeRange(BaseModel):
    start: str
    end: str


class QueryRequest(BaseModel):
    query: str = Field(..., description="The user query to process", min_length=1, max_length=2000)
    lane_hint: Optional[str] = Field(None, description="Hint for the data lane to use (stocks, macro, regulation)")
    time_range: Optional[TimeRange] = None
    top_k: Optional[int] = Field(8, ge=1, le=20, description="Number of results to return")
    include_citations: Optional[bool] = True


class Citation(BaseModel):
    source_title: str
    source_url: str
    chunk_id: str
    quote: str


class QueryResponse(BaseModel):
    answer: str
    citations: Optional[List[Citation]] = []
    metadata: Optional[Dict[str, Any]] = {}


class IngestRequest(BaseModel):
    lane: str = Field(..., description="Data lane to ingest into (stocks, macro, regulation)")
    source_urls: Optional[List[str]] = []
    documents: Optional[List[Dict[str, Any]]] = []


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    details: Optional[Dict[str, Any]] = {}