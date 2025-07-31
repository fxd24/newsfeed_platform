from pydantic import BaseModel

from src.models.domain import NewsEvent


class IngestResponse(BaseModel):
    """Response model for /ingest endpoint"""
    status: str
    message: str


class RetrieveResponse(BaseModel):
    """Response model for /retrieve endpoint"""
    events: list[NewsEvent]
    total_count: int

