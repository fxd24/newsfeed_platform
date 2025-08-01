"""
Scheduler manager for coordinating background polling jobs.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from src.sources.factory import SourceManager
from src.services import IngestionService

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manager for APScheduler background jobs"""
    
    def __init__(self, source_manager: SourceManager, ingestion_service: IngestionService):
        self.source_manager = source_manager
        self.ingestion_service = ingestion_service
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone='UTC'
        )
        self.jobs: dict[str, str] = {}  # source_name -> job_id
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Scheduler shutdown")
    
    def add_source_job(self, source_name: str, poll_interval: int) -> bool:
        """Add a polling job for a source"""
        try:
            # Remove existing job if it exists
            if source_name in self.jobs:
                self.remove_source_job(source_name)
            
            # Create job function
            async def poll_source():
                await self._poll_source(source_name)
            
            # Add job to scheduler
            job = self.scheduler.add_job(
                poll_source,
                trigger=IntervalTrigger(seconds=poll_interval),
                id=f"poll_{source_name}",
                name=f"Poll {source_name}",
                replace_existing=True
            )
            
            self.jobs[source_name] = job.id
            self.logger.info(f"Added polling job for {source_name} (interval: {poll_interval}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding job for {source_name}: {e}")
            return False
    
    def remove_source_job(self, source_name: str) -> bool:
        """Remove a polling job for a source"""
        try:
            job_id = self.jobs.get(source_name)
            if job_id:
                self.scheduler.remove_job(job_id)
                del self.jobs[source_name]
                self.logger.info(f"Removed polling job for {source_name}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing job for {source_name}: {e}")
            return False
    
    def update_source_job(self, source_name: str, poll_interval: int) -> bool:
        """Update a polling job's interval"""
        try:
            # Remove and re-add the job with new interval
            if self.remove_source_job(source_name):
                return self.add_source_job(source_name, poll_interval)
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating job for {source_name}: {e}")
            return False
    
    def add_all_source_jobs(self) -> int:
        """Add polling jobs for all enabled sources"""
        added_count = 0
        
        for source in self.source_manager.get_enabled_sources():
            if self.add_source_job(source.config.name, source.get_poll_interval()):
                added_count += 1
        
        self.logger.info(f"Added {added_count} polling jobs")
        return added_count
    
    def remove_all_jobs(self):
        """Remove all polling jobs"""
        for source_name in list(self.jobs.keys()):
            self.remove_source_job(source_name)
        self.logger.info("Removed all polling jobs")
    
    async def _poll_source(self, source_name: str):
        """Poll a specific source and ingest events"""
        try:
            self.logger.debug(f"Polling source: {source_name}")
            
            # Fetch events from source
            events = await self.source_manager.fetch_source_events(source_name)
            
            if events:
                # Ingest events
                result = await self.ingestion_service.ingest_events(events)
                
                if result['ingested_count'] > 0:
                    self.logger.info(
                        f"Polled {source_name}: {result['ingested_count']} events ingested"
                    )
                else:
                    self.logger.debug(f"Polled {source_name}: no new events")
            else:
                self.logger.debug(f"Polled {source_name}: no events returned")
                
        except Exception as e:
            self.logger.error(f"Error polling {source_name}: {e}")
    
    async def poll_all_sources(self):
        """Poll all enabled sources immediately"""
        self.logger.info("Polling all sources")
        
        for source in self.source_manager.get_enabled_sources():
            await self._poll_source(source.config.name)
    
    def get_job_status(self) -> dict[str, dict]:
        """Get status of all jobs"""
        status = {}
        
        for source_name, job_id in self.jobs.items():
            job = self.scheduler.get_job(job_id)
            if job:
                status[source_name] = {
                    'job_id': job_id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
            else:
                status[source_name] = {
                    'job_id': job_id,
                    'status': 'not_found'
                }
        
        return status
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler.running
    
    def get_job_count(self) -> int:
        """Get number of active jobs"""
        return len(self.jobs) 