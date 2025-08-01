"""
Test the new architecture components.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.sources import SourceConfig, UniversalNewsSource
from src.sources.fetchers import MockFetcher
from src.sources.adapters import GitHubStatusAdapter
from src.sources.factory import SourceFactory, SourceManager
from src.services import IngestionService
from src.config import ConfigManager


class TestSourceArchitecture:
    """Test the source architecture components"""
    
    def test_source_config_creation(self):
        """Test creating a source configuration"""
        config = SourceConfig(
            name="test_source",
            enabled=True,
            poll_interval=300,
            source_type="json_api",
            adapter_class="GitHubStatusAdapter",
            url="https://api.example.com/status"
        )
        
        assert config.name == "test_source"
        assert config.enabled is True
        assert config.poll_interval == 300
        assert config.source_type == "json_api"
        assert config.adapter_class == "GitHubStatusAdapter"
        assert config.url == "https://api.example.com/status"
    
    def test_universal_news_source_creation(self):
        """Test creating a UniversalNewsSource"""
        config = SourceConfig(
            name="test_source",
            url="https://api.example.com/status"
        )
        
        fetcher = MockFetcher({"incidents": []})
        adapter = GitHubStatusAdapter()
        
        source = UniversalNewsSource(config, fetcher, adapter)
        
        assert source.config.name == "test_source"
        assert source.is_enabled() is True
        assert source.get_poll_interval() == 300
    
    @pytest.mark.asyncio
    async def test_universal_news_source_fetch(self):
        """Test fetching events from a UniversalNewsSource"""
        # Mock data that GitHub adapter expects
        mock_data = {
            "incidents": [
                {
                    "name": "Test Incident",
                    "body": "This is a test incident",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            ]
        }
        
        config = SourceConfig(
            name="test_source",
            url="https://api.example.com/status"
        )
        
        fetcher = MockFetcher(mock_data)
        adapter = GitHubStatusAdapter()
        
        source = UniversalNewsSource(config, fetcher, adapter)
        
        events = await source.get_events()
        
        assert len(events) == 1
        assert events[0].title == "Test Incident"
        assert events[0].source == "GitHub Status"
        assert events[0].body == "This is a test incident"
    
    def test_source_factory(self):
        """Test the source factory"""
        factory = SourceFactory()
        
        config = SourceConfig(
            name="test_source",
            source_type="mock",
            adapter_class="GitHubStatusAdapter",
            url="https://api.example.com/status"
        )
        
        source = factory.create_source(config)
        
        assert isinstance(source, UniversalNewsSource)
        assert source.config.name == "test_source"
    
    def test_source_manager(self):
        """Test the source manager"""
        manager = SourceManager()
        
        config = SourceConfig(
            name="test_source",
            url="https://api.example.com/status"
        )
        
        # Add source
        success = manager.add_source(config)
        assert success is True
        
        # Get source
        source = manager.get_source("test_source")
        assert source is not None
        assert source.config.name == "test_source"
        
        # Get enabled sources
        enabled_sources = manager.get_enabled_sources()
        assert len(enabled_sources) == 1
        
        # Remove source
        success = manager.remove_source("test_source")
        assert success is True
        
        # Verify removed
        source = manager.get_source("test_source")
        assert source is None


class TestConfiguration:
    """Test configuration management"""
    
    def test_config_manager_from_dict(self):
        """Test loading configuration from dictionary"""
        config_data = {
            "sources": {
                "github_status": {
                    "enabled": True,
                    "poll_interval": 300,
                    "source_type": "json_api",
                    "adapter_class": "GitHubStatusAdapter",
                    "url": "https://www.githubstatus.com/api/v2/incidents.json"
                }
            }
        }
        
        manager = ConfigManager()
        success = manager.load_from_dict(config_data)
        
        assert success is True
        assert len(manager.get_source_configs()) == 1
        
        config = manager.get_source_config("github_status")
        assert config is not None
        assert config.name == "github_status"
        assert config.enabled is True
        assert config.poll_interval == 300
    
    def test_config_validation(self):
        """Test configuration validation"""
        manager = ConfigManager()
        
        # Valid config
        valid_config = {
            "sources": {
                "valid_source": {
                    "url": "https://api.example.com",
                    "adapter_class": "GitHubStatusAdapter"
                }
            }
        }
        
        manager.load_from_dict(valid_config)
        errors = manager.validate_configs()
        assert len(errors) == 0
        
        # Invalid config (missing URL)
        invalid_config = {
            "sources": {
                "invalid_source": {
                    "adapter_class": "GitHubStatusAdapter"
                }
            }
        }
        
        manager.load_from_dict(invalid_config)
        errors = manager.validate_configs()
        assert len(errors) > 0
        assert any("Missing URL" in error for error in errors)


class TestIngestionService:
    """Test the ingestion service"""
    
    @pytest.mark.asyncio
    async def test_ingestion_service(self):
        """Test the ingestion service"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.create_events = Mock()
        mock_repository.count_events = Mock(return_value=10)
        
        service = IngestionService(mock_repository)
        
        # Test with valid events
        from src.models.domain import NewsEvent
        
        events = [
            NewsEvent(
                id="test-1",
                source="Test Source",
                title="Test Event 1",
                body="Test body 1",
                published_at=datetime.now(timezone.utc)
            ),
            NewsEvent(
                id="test-2",
                source="Test Source",
                title="Test Event 2",
                body="Test body 2",
                published_at=datetime.now(timezone.utc)
            )
        ]
        
        result = await service.ingest_events(events)
        
        assert result['success'] is True
        assert result['ingested_count'] == 2
        assert result['skipped_count'] == 0
        assert len(result['errors']) == 0
        
        # Verify repository was called
        assert mock_repository.create_events.call_count == 2
    
    @pytest.mark.asyncio
    async def test_ingestion_service_validation(self):
        """Test ingestion service validation"""
        mock_repository = Mock()
        mock_repository.create_events = Mock()
        
        service = IngestionService(mock_repository)
        
        # Test with invalid event (missing title)
        from src.models.domain import NewsEvent
        
        invalid_event = NewsEvent(
            id="test-1",
            source="Test Source",
            title="",  # Empty title
            body="Test body",
            published_at=datetime.now(timezone.utc)
        )
        
        result = await service.ingest_events([invalid_event])
        
        assert result['ingested_count'] == 0
        assert result['skipped_count'] == 1
        assert mock_repository.create_events.call_count == 0 