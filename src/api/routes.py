from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Any
import logging

from src.models.domain import NewsEvent
from src.models.api import IngestResponse
from src.repositories.news_event_repository import NewsEventRepository
from src.services import IngestionService
from src.sources.factory import SourceManager
from src.scheduler import SchedulerManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_repository(request: Request) -> NewsEventRepository:
    """Get the repository instance from FastAPI app state"""
    if not hasattr(request.app.state, 'repository'):
        raise HTTPException(status_code=500, detail="Repository not initialized")
    return request.app.state.repository


def get_ingestion_service(request: Request) -> IngestionService:
    """Get the ingestion service instance from FastAPI app state"""
    if not hasattr(request.app.state, 'ingestion_service'):
        raise HTTPException(status_code=500, detail="Ingestion service not initialized")
    return request.app.state.ingestion_service


def get_source_manager(request: Request) -> SourceManager:
    """Get the source manager instance from FastAPI app state"""
    if not hasattr(request.app.state, 'source_manager'):
        raise HTTPException(status_code=500, detail="Source manager not initialized")
    return request.app.state.source_manager


def get_scheduler_manager(request: Request) -> SchedulerManager:
    """Get the scheduler manager instance from FastAPI app state"""
    if not hasattr(request.app.state, 'scheduler_manager'):
        raise HTTPException(status_code=500, detail="Scheduler manager not initialized")
    return request.app.state.scheduler_manager


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    events: list[dict[str, Any]], 
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Accept JSON array and store events using the ingestion service"""
    try:
        # Validate and parse events using Pydantic
        validated_events = [NewsEvent(**event) for event in events]
        
        # Use ingestion service to store events
        result = await ingestion_service.ingest_events(validated_events)
        
        logger.info(f"Ingested {result['ingested_count']} events, skipped {result['skipped_count']}")
        
        return IngestResponse(
            status="ok" if result['success'] else "partial",
            message=f"Successfully ingested {result['ingested_count']} events, skipped {result['skipped_count']}"
        )
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid event format: {str(e)}"
        )


@router.get("/retrieve", response_model=list[NewsEvent])
async def retrieve_events(
    repository: NewsEventRepository = Depends(get_repository),
    limit: int = 100,
    days_back: int = 14,
    alpha: float = 0.7,
    decay_param: float = 0.02
):
    """Return filtered events relevant to IT managers using hybrid relevancy + recency scoring
    
    Args:
        limit: Maximum number of results to return
        days_back: Only return events from the last N days
        alpha: Weight for relevancy vs recency (0.7 = 70% relevancy, 30% recency)
        decay_param: Exponential decay parameter for recency scoring (0.02 = 2% decay per day)
    """
    try:
        # IT Manager focused query for major outages, cybersecurity threats, and critical software bugs
        it_manager_query = """
        major outage critical incident service disruption system failure
        cybersecurity threat security breach vulnerability exploit malware ransomware
        critical software bug severe bug production issue data loss
        emergency maintenance urgent fix hotfix patch
        """
        
        # Use semantic search if repository supports it (ChromaDB)
        if hasattr(repository, 'search_events'):
            events = repository.search_events(
                it_manager_query, 
                limit=limit, 
                days_back=days_back,
                alpha=alpha,
                decay_param=decay_param
            )
            logger.info(f"Retrieved {len(events)} IT-relevant events using hybrid scoring (α={alpha}, decay={decay_param})")
        else:
            # Fallback to all events for in-memory repository
            events = repository.get_all_events()
            logger.info(f"Retrieved {len(events)} events from {repository.__class__.__name__} (no semantic search)")
        
        return events
        
    except Exception as e:
        logger.error(f"Error during retrieval: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.get("/retrieve/all", response_model=list[NewsEvent])
async def retrieve_all_events(repository: NewsEventRepository = Depends(get_repository)):
    """Return all stored events without filtering"""
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


# Admin endpoints for managing sources and polling

@router.post("/admin/poll/all")
async def poll_all_sources(
    scheduler_manager: SchedulerManager = Depends(get_scheduler_manager)
):
    """Manually trigger polling of all enabled sources"""
    try:
        await scheduler_manager.poll_all_sources()
        return {"status": "ok", "message": "Polling all sources completed"}
    except Exception as e:
        logger.error(f"Error polling all sources: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to poll sources: {str(e)}"
        )


@router.post("/admin/poll/{source_name}")
async def poll_source(
    source_name: str,
    source_manager: SourceManager = Depends(get_source_manager),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Manually trigger polling of a specific source"""
    try:
        events = await source_manager.fetch_source_events(source_name)
        if events:
            result = await ingestion_service.ingest_events(events)
            return {
                "status": "ok",
                "message": f"Polled {source_name}: {result['ingested_count']} events ingested"
            }
        else:
            return {
                "status": "ok",
                "message": f"Polled {source_name}: no events returned"
            }
    except Exception as e:
        logger.error(f"Error polling source {source_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to poll source {source_name}: {str(e)}"
        )


@router.get("/admin/sources")
async def get_sources_status(
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Get status of all sources"""
    try:
        return {
            "sources": source_manager.get_source_status(),
            "enabled_count": len(source_manager.get_enabled_sources()),
            "total_count": len(source_manager.get_all_sources())
        }
    except Exception as e:
        logger.error(f"Error getting sources status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sources status: {str(e)}"
        )


@router.get("/admin/scheduler")
async def get_scheduler_status(
    scheduler_manager: SchedulerManager = Depends(get_scheduler_manager)
):
    """Get status of the scheduler"""
    try:
        return {
            "running": scheduler_manager.is_running(),
            "job_count": scheduler_manager.get_job_count(),
            "job_status": scheduler_manager.get_job_status()
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


@router.get("/admin/stats")
async def get_ingestion_stats(
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Get ingestion statistics"""
    try:
        return ingestion_service.get_ingestion_stats()
    except Exception as e:
        logger.error(f"Error getting ingestion stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ingestion stats: {str(e)}"
        )

