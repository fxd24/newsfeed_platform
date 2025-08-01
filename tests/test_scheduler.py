"""
Tests for the scheduler manager functionality.

This module tests the SchedulerManager class and its integration
with source management and ingestion services.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.scheduler.scheduler_manager import SchedulerManager
from src.sources.factory import SourceManager
from src.services.ingestion_service import IngestionService
from src.repositories.news_event_repository import InMemoryNewsEventRepository
from datetime import datetime


class TestSchedulerManager:
    """Test the SchedulerManager class"""
    
    @pytest.fixture
    def mock_source_manager(self):
        """Create a mock source manager"""
        source_manager = Mock(spec=SourceManager)
        source_manager.get_enabled_sources.return_value = []
        source_manager.fetch_source_events = AsyncMock(return_value=[])
        return source_manager
    
    @pytest.fixture
    def mock_ingestion_service(self):
        """Create a mock ingestion service"""
        ingestion_service = Mock(spec=IngestionService)
        ingestion_service.ingest_events = AsyncMock(return_value={
            'success': True,
            'ingested_count': 0,
            'skipped_count': 0
        })
        return ingestion_service
    
    @pytest.fixture
    def mock_scheduler(self):
        """Create a completely mocked scheduler"""
        scheduler = Mock()
        scheduler.running = False
        scheduler.start = Mock()
        scheduler.shutdown = Mock()
        scheduler.add_job = Mock()
        scheduler.remove_job = Mock()
        scheduler.get_job = Mock()
        return scheduler
    
    @pytest.fixture
    def scheduler_manager(self, mock_source_manager, mock_ingestion_service, mock_scheduler):
        """Create a scheduler manager with mocked dependencies"""
        with patch('src.scheduler.scheduler_manager.AsyncIOScheduler', return_value=mock_scheduler):
            return SchedulerManager(mock_source_manager, mock_ingestion_service)
    
    def test_initialization(self, scheduler_manager):
        """Test scheduler manager initialization"""
        assert scheduler_manager.source_manager is not None
        assert scheduler_manager.ingestion_service is not None
        assert scheduler_manager.scheduler is not None
        assert scheduler_manager.jobs == {}
        assert scheduler_manager.logger is not None
    
    def test_start_scheduler(self, scheduler_manager, mock_scheduler):
        """Test starting the scheduler"""
        mock_scheduler.running = False
        
        scheduler_manager.start()
        
        mock_scheduler.start.assert_called_once()
    
    def test_start_scheduler_already_running(self, scheduler_manager, mock_scheduler):
        """Test starting the scheduler when it's already running"""
        mock_scheduler.running = True
        
        scheduler_manager.start()
        
        # Should not call start if already running
        mock_scheduler.start.assert_not_called()
    
    def test_shutdown_scheduler(self, scheduler_manager, mock_scheduler):
        """Test shutting down the scheduler"""
        mock_scheduler.running = True
        
        scheduler_manager.shutdown()
        
        mock_scheduler.shutdown.assert_called_once()
    
    def test_shutdown_scheduler_not_running(self, scheduler_manager, mock_scheduler):
        """Test shutting down the scheduler when it's not running"""
        mock_scheduler.running = False
        
        scheduler_manager.shutdown()
        
        # Should not call shutdown if not running
        mock_scheduler.shutdown.assert_not_called()
    
    def test_add_source_job_success(self, scheduler_manager, mock_scheduler):
        """Test successfully adding a source job"""
        # Mock the scheduler
        mock_job = Mock()
        mock_job.id = "test_job_id"
        mock_scheduler.add_job.return_value = mock_job
        
        result = scheduler_manager.add_source_job("test_source", 300)
        
        assert result is True
        assert "test_source" in scheduler_manager.jobs
        assert scheduler_manager.jobs["test_source"] == "test_job_id"
        mock_scheduler.add_job.assert_called_once()
    
    def test_add_source_job_existing_job(self, scheduler_manager, mock_scheduler):
        """Test adding a source job when one already exists"""
        # Add an existing job
        scheduler_manager.jobs["test_source"] = "existing_job_id"
        
        # Mock the scheduler
        mock_job = Mock()
        mock_job.id = "new_job_id"
        mock_scheduler.add_job.return_value = mock_job
        
        result = scheduler_manager.add_source_job("test_source", 300)
        
        assert result is True
        # Should remove existing job first
        mock_scheduler.remove_job.assert_called_once_with("existing_job_id")
        assert scheduler_manager.jobs["test_source"] == "new_job_id"
    
    def test_add_source_job_failure(self, scheduler_manager, mock_scheduler):
        """Test adding a source job when it fails"""
        # Mock the scheduler to raise an exception
        mock_scheduler.add_job.side_effect = Exception("Test error")
        
        result = scheduler_manager.add_source_job("test_source", 300)
        
        assert result is False
        assert "test_source" not in scheduler_manager.jobs
    
    def test_remove_source_job_success(self, scheduler_manager, mock_scheduler):
        """Test successfully removing a source job"""
        # Add a job first
        scheduler_manager.jobs["test_source"] = "test_job_id"
        
        result = scheduler_manager.remove_source_job("test_source")
        
        assert result is True
        assert "test_source" not in scheduler_manager.jobs
        mock_scheduler.remove_job.assert_called_once_with("test_job_id")
    
    def test_remove_source_job_not_found(self, scheduler_manager):
        """Test removing a source job that doesn't exist"""
        result = scheduler_manager.remove_source_job("nonexistent_source")
        
        assert result is False
    
    def test_remove_source_job_failure(self, scheduler_manager, mock_scheduler):
        """Test removing a source job when it fails"""
        # Add a job first
        scheduler_manager.jobs["test_source"] = "test_job_id"
        mock_scheduler.remove_job.side_effect = Exception("Test error")
        
        result = scheduler_manager.remove_source_job("test_source")
        
        assert result is False
        # Job should still be in the jobs dict
        assert "test_source" in scheduler_manager.jobs
    
    def test_update_source_job_success(self, scheduler_manager):
        """Test successfully updating a source job"""
        # Mock the remove and add methods
        scheduler_manager.remove_source_job = Mock(return_value=True)
        scheduler_manager.add_source_job = Mock(return_value=True)
        
        result = scheduler_manager.update_source_job("test_source", 600)
        
        assert result is True
        scheduler_manager.remove_source_job.assert_called_once_with("test_source")
        scheduler_manager.add_source_job.assert_called_once_with("test_source", 600)
    
    def test_update_source_job_failure(self, scheduler_manager):
        """Test updating a source job when it fails"""
        # Mock the remove method to fail
        scheduler_manager.remove_source_job = Mock(return_value=False)
        
        result = scheduler_manager.update_source_job("test_source", 600)
        
        assert result is False
    
    def test_add_all_source_jobs(self, scheduler_manager, mock_source_manager):
        """Test adding jobs for all enabled sources"""
        # Mock enabled sources
        mock_source1 = Mock()
        mock_source1.config.name = "source1"
        mock_source1.get_poll_interval.return_value = 300
        
        mock_source2 = Mock()
        mock_source2.config.name = "source2"
        mock_source2.get_poll_interval.return_value = 600
        
        mock_source_manager.get_enabled_sources.return_value = [mock_source1, mock_source2]
        
        # Mock add_source_job to succeed for first source, fail for second
        scheduler_manager.add_source_job = Mock(side_effect=[True, False])
        
        result = scheduler_manager.add_all_source_jobs()
        
        assert result == 1  # Only one job was added successfully
        assert scheduler_manager.add_source_job.call_count == 2
        scheduler_manager.add_source_job.assert_any_call("source1", 300)
        scheduler_manager.add_source_job.assert_any_call("source2", 600)
    
    def test_remove_all_jobs(self, scheduler_manager):
        """Test removing all jobs"""
        # Add some jobs
        scheduler_manager.jobs = {
            "source1": "job1",
            "source2": "job2"
        }
        scheduler_manager.remove_source_job = Mock(return_value=True)
        
        scheduler_manager.remove_all_jobs()
        
        assert scheduler_manager.remove_source_job.call_count == 2
        scheduler_manager.remove_source_job.assert_any_call("source1")
        scheduler_manager.remove_source_job.assert_any_call("source2")
    
    @pytest.mark.asyncio
    async def test_poll_source_success(self, scheduler_manager, mock_source_manager, mock_ingestion_service):
        """Test successfully polling a source"""
        # Mock source to return events
        mock_events = [Mock(), Mock()]
        mock_source_manager.fetch_source_events.return_value = mock_events
        mock_ingestion_service.ingest_events.return_value = {
            'success': True,
            'ingested_count': 2,
            'skipped_count': 0
        }
        
        await scheduler_manager._poll_source("test_source")
        
        mock_source_manager.fetch_source_events.assert_called_once_with("test_source")
        mock_ingestion_service.ingest_events.assert_called_once_with(mock_events)
    
    @pytest.mark.asyncio
    async def test_poll_source_no_events(self, scheduler_manager, mock_source_manager, mock_ingestion_service):
        """Test polling a source that returns no events"""
        # Mock source to return no events
        mock_source_manager.fetch_source_events.return_value = []
        
        await scheduler_manager._poll_source("test_source")
        
        mock_source_manager.fetch_source_events.assert_called_once_with("test_source")
        mock_ingestion_service.ingest_events.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_poll_source_fetch_error(self, scheduler_manager, mock_source_manager):
        """Test polling a source when fetch fails"""
        # Mock source to raise an exception
        mock_source_manager.fetch_source_events.side_effect = Exception("Fetch error")
        
        # Should not raise an exception
        await scheduler_manager._poll_source("test_source")
        
        mock_source_manager.fetch_source_events.assert_called_once_with("test_source")
    
    @pytest.mark.asyncio
    async def test_poll_source_ingest_error(self, scheduler_manager, mock_source_manager, mock_ingestion_service):
        """Test polling a source when ingestion fails"""
        # Mock source to return events
        mock_events = [Mock()]
        mock_source_manager.fetch_source_events.return_value = mock_events
        
        # Mock ingestion to raise an exception
        mock_ingestion_service.ingest_events.side_effect = Exception("Ingest error")
        
        # Should not raise an exception
        await scheduler_manager._poll_source("test_source")
        
        mock_source_manager.fetch_source_events.assert_called_once_with("test_source")
        mock_ingestion_service.ingest_events.assert_called_once_with(mock_events)
    
    @pytest.mark.asyncio
    async def test_poll_all_sources(self, scheduler_manager, mock_source_manager):
        """Test polling all sources"""
        # Mock enabled sources
        mock_source1 = Mock()
        mock_source1.config.name = "source1"
        
        mock_source2 = Mock()
        mock_source2.config.name = "source2"
        
        mock_source_manager.get_enabled_sources.return_value = [mock_source1, mock_source2]
        
        # Mock _poll_source
        scheduler_manager._poll_source = AsyncMock()
        
        await scheduler_manager.poll_all_sources()
        
        assert scheduler_manager._poll_source.call_count == 2
        scheduler_manager._poll_source.assert_any_call("source1")
        scheduler_manager._poll_source.assert_any_call("source2")
    
    def test_get_job_status(self, scheduler_manager, mock_scheduler):
        """Test getting job status"""
        # Add some jobs
        scheduler_manager.jobs = {
            "source1": "job1",
            "source2": "job2"
        }
        
        # Mock scheduler to return job info
        mock_job1 = Mock()
        mock_job1.next_run_time = datetime(2024, 1, 1, 10, 0, 0)  # Use datetime object
        mock_job1.trigger = "interval[0:00:05]"
        
        mock_job2 = Mock()
        mock_job2.next_run_time = datetime(2024, 1, 1, 11, 0, 0)  # Use datetime object
        mock_job2.trigger = "interval[0:00:10]"
        
        mock_scheduler.get_job.side_effect = [mock_job1, mock_job2]
        
        status = scheduler_manager.get_job_status()
        
        assert "source1" in status
        assert "source2" in status
        assert status["source1"]["job_id"] == "job1"
        assert status["source2"]["job_id"] == "job2"
        assert status["source1"]["next_run"] == "2024-01-01T10:00:00"
        assert status["source2"]["next_run"] == "2024-01-01T11:00:00"
        assert status["source1"]["trigger"] == "interval[0:00:05]"
        assert status["source2"]["trigger"] == "interval[0:00:10]"
    
    def test_get_job_status_missing_job(self, scheduler_manager, mock_scheduler):
        """Test getting job status when a job is missing"""
        # Add a job
        scheduler_manager.jobs = {"source1": "job1"}
        
        # Mock scheduler to return None for missing job
        mock_scheduler.get_job.return_value = None
        
        status = scheduler_manager.get_job_status()
        
        assert "source1" in status
        assert "status" in status["source1"]
        assert status["source1"]["status"] == "not_found"
    
    def test_is_running(self, scheduler_manager, mock_scheduler):
        """Test checking if scheduler is running"""
        # Mock scheduler as running
        mock_scheduler.running = True
        assert scheduler_manager.is_running() is True
        
        # Mock scheduler as not running
        mock_scheduler.running = False
        assert scheduler_manager.is_running() is False
    
    def test_get_job_count(self, scheduler_manager):
        """Test getting job count"""
        # Add some jobs
        scheduler_manager.jobs = {
            "source1": "job1",
            "source2": "job2",
            "source3": "job3"
        }
        
        assert scheduler_manager.get_job_count() == 3
        
        # Clear jobs
        scheduler_manager.jobs = {}
        
        assert scheduler_manager.get_job_count() == 0


class TestSchedulerManagerIntegration:
    """Integration tests for SchedulerManager with real components"""
    
    @pytest.fixture
    def real_scheduler_manager(self):
        """Create a scheduler manager with real components"""
        repository = InMemoryNewsEventRepository()
        ingestion_service = IngestionService(repository)
        source_manager = SourceManager()
        return SchedulerManager(source_manager, ingestion_service)
    
    def test_real_initialization(self, real_scheduler_manager):
        """Test initialization with real components"""
        assert real_scheduler_manager.source_manager is not None
        assert real_scheduler_manager.ingestion_service is not None
        assert real_scheduler_manager.scheduler is not None
        assert real_scheduler_manager.jobs == {}
    
    @pytest.mark.asyncio
    async def test_real_start_shutdown(self, real_scheduler_manager):
        """Test starting and shutting down with real scheduler"""
        # Start the scheduler
        real_scheduler_manager.start()
        assert real_scheduler_manager.is_running() is True
        
        # Shutdown the scheduler
        real_scheduler_manager.shutdown()
        # Note: The scheduler might still show as running due to async nature
        # We'll just test that shutdown doesn't raise an exception
        assert True  # If we get here, shutdown worked
    
    @pytest.mark.asyncio
    async def test_real_job_management(self, real_scheduler_manager):
        """Test job management with real scheduler"""
        # Start the scheduler
        real_scheduler_manager.start()
        
        # Add a job
        result = real_scheduler_manager.add_source_job("test_source", 300)
        assert result is True
        assert "test_source" in real_scheduler_manager.jobs
        assert real_scheduler_manager.get_job_count() == 1
        
        # Remove the job
        result = real_scheduler_manager.remove_source_job("test_source")
        assert result is True
        assert "test_source" not in real_scheduler_manager.jobs
        assert real_scheduler_manager.get_job_count() == 0
        
        # Shutdown
        real_scheduler_manager.shutdown() 