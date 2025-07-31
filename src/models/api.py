from pydantic import BaseModel



class IngestResponse(BaseModel):
    """Response model for /ingest endpoint"""
    status: str
    message: str


# TODO future work improvement: RetrieveResponse that does not follow list[NewsEvent] because it follows API best practices