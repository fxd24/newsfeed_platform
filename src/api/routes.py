from fastapi import APIRouter, HTTPException
from typing import Any
import logging

from src.models.domain import NewsEvent
from src.models.api import IngestResponse, RetrieveResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Simple in-memory storage
events_storage: list[NewsEvent] = []


@router.post("/ingest", response_model=IngestResponse)
def ingest_events(events: list[dict[str, Any]]):
    """Accept JSON array and store events"""
    try:
        # Validate and parse events using Pydantic
        validated_events = [NewsEvent(**event) for event in events]
        
        # Store the events
        events_storage.extend(validated_events)
        
        logger.info(f"Stored {len(validated_events)} events")
        
        return IngestResponse(
            status="ok",
            message=f"Successfully stored {len(validated_events)} events"
        )
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid event format: {str(e)}"
        )


@router.get("/retrieve", response_model=RetrieveResponse)
def retrieve_events():
    """Return all stored events"""
    logger.info(f"Retrieved {len(events_storage)} events")
    
    return RetrieveResponse(
        events=events_storage,
        total_count=len(events_storage)
    )