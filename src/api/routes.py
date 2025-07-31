from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Any
import logging

from src.models.domain import NewsEvent
from src.models.api import IngestResponse
from src.repositories.news_event_repository import NewsEventRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_repository(request: Request) -> NewsEventRepository:
    """Get the repository instance from FastAPI app state"""
    return request.app.state.repository


@router.post("/ingest", response_model=IngestResponse)
def ingest_events(
    events: list[dict[str, Any]], 
    repository: NewsEventRepository = Depends(get_repository)
):
    """Accept JSON array and store events"""
    try:
        # Validate and parse events using Pydantic
        validated_events = [NewsEvent(**event) for event in events]
        
        # Store the events using repository
        repository.create_events(validated_events)
        
        logger.info(f"Stored {len(validated_events)} events using {repository.__class__.__name__}")
        
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


@router.get("/retrieve", response_model=list[NewsEvent])
def retrieve_events(repository: NewsEventRepository = Depends(get_repository)):
    """Return all stored events"""
    try:
        events = repository.get_all_events()
        
        logger.info(f"Retrieved {len(events)} events from {repository.__class__.__name__}")
        
        return events
        
    except Exception as e:
        logger.error(f"Error during retrieval: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve events: {str(e)}"
        )

