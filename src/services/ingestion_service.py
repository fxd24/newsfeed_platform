"""
Ingestion service for processing news events.

This service handles the ingestion of news events from both polling
sources and external API calls, providing a unified interface.
"""

import logging
from datetime import datetime, timezone

from src.models.domain import NewsEvent
from src.repositories.news_event_repository import NewsEventRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting news events from various sources"""
    
    def __init__(self, repository: NewsEventRepository):
        self.repository = repository
        self.logger = logging.getLogger(__name__)
    
    async def ingest_events(self, events: list[NewsEvent]) -> dict:
        """
        Ingest a list of news events.
        
        This method handles both polling events and external API events,
        providing a unified ingestion interface.
        """
        if not events:
            return {
                'success': True,
                'ingested_count': 0,
                'skipped_count': 0,
                'errors': []
            }
        
        ingested_count = 0
        skipped_count = 0
        errors = []
        
        for event in events:
            try:
                # Validate event
                if not self._validate_event(event):
                    skipped_count += 1
                    continue
                
                # Check for duplicates (optional - could be disabled for performance)
                if self._is_duplicate(event):
                    skipped_count += 1
                    self.logger.debug(f"Skipping duplicate event: {event.title}")
                    continue
                
                # Store event
                self.repository.create_events([event])
                ingested_count += 1
                
                self.logger.debug(f"Ingested event: {event.title} from {event.source}")
                
            except Exception as e:
                error_msg = f"Error ingesting event {event.title}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                skipped_count += 1
        
        # Log summary
        if ingested_count > 0:
            self.logger.info(f"Ingestion complete: {ingested_count} ingested, {skipped_count} skipped")
        
        if errors:
            self.logger.warning(f"Ingestion completed with {len(errors)} errors")
        
        return {
            'success': len(errors) == 0,
            'ingested_count': ingested_count,
            'skipped_count': skipped_count,
            'errors': errors
        }
    
    async def ingest_single_event(self, event: NewsEvent) -> dict:
        """Ingest a single news event"""
        return await self.ingest_events([event])
    
    def _validate_event(self, event: NewsEvent) -> bool:
        """Validate a news event"""
        if not event.title or not event.title.strip():
            self.logger.warning("Event missing title")
            return False
        
        if not event.source or not event.source.strip():
            self.logger.warning("Event missing source")
            return False
        
        if not event.published_at:
            self.logger.warning("Event missing published_at")
            return False
        
        # Ensure both dates are timezone-aware for comparison
        current_utc = datetime.now(timezone.utc)
        
        # If event.published_at is timezone-naive, assume it's UTC
        if event.published_at.tzinfo is None:
            event_published_utc = event.published_at.replace(tzinfo=timezone.utc)
        else:
            event_published_utc = event.published_at
        
        # Check if event is too far in the future (allow 1 hour for timezone differences)
        if event_published_utc > current_utc:
            time_diff = event_published_utc - current_utc
            if time_diff.total_seconds() > 3600:  # 1 hour
                self.logger.warning(f"Event published_at is too far in the future: {event_published_utc} > {current_utc}")
                return False
        
        return True
    
    def _is_duplicate(self, event: NewsEvent) -> bool:
        """
        Check if an event is a duplicate.
        
        This is a simple implementation that could be enhanced with
        more sophisticated duplicate detection (e.g., fuzzy matching).
        """
        try:
            # TODO: Implement proper duplicate detection
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for duplicates: {e}")
            return False
    
    def get_ingestion_stats(self) -> dict:
        """Get ingestion statistics"""
        try:
            total_events = self.repository.count_events()
            
            # Could add more sophisticated stats here
            # - Events per source
            # - Events per time period
            # - Ingestion rate
            
            return {
                'total_events': total_events,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ingestion stats: {e}")
            return {
                'total_events': 0,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            } 