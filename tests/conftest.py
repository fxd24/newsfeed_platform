"""
Test configuration and fixtures for the newsfeed platform.

This module provides test fixtures and configuration that work with
the new architecture components.
"""

import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient

from src.main import app
from src.repositories.news_event_repository import InMemoryNewsEventRepository, ChromaDBNewsEventRepository
from src.services import IngestionService
from src.sources.factory import SourceManager
from src.scheduler import SchedulerManager
from src.config import ConfigManager


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def in_memory_repository():
    """Create an in-memory repository for testing"""
    return InMemoryNewsEventRepository()


@pytest.fixture
def chroma_repository(temp_chroma_dir):
    """Create a ChromaDB repository for testing"""
    return ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)


@pytest.fixture
def ingestion_service(in_memory_repository):
    """Create an ingestion service with in-memory repository"""
    return IngestionService(in_memory_repository)


@pytest.fixture
def source_manager():
    """Create a source manager for testing"""
    return SourceManager()


@pytest.fixture
def scheduler_manager(source_manager, ingestion_service):
    """Create a scheduler manager for testing"""
    return SchedulerManager(source_manager, ingestion_service)


@pytest.fixture
def config_manager():
    """Create a config manager for testing"""
    return ConfigManager()


@pytest.fixture
def test_app(in_memory_repository, ingestion_service, source_manager, scheduler_manager, config_manager):
    """Create a test app with all components initialized"""
    # Set up the app state with test components
    app.state.repository = in_memory_repository
    app.state.ingestion_service = ingestion_service
    app.state.source_manager = source_manager
    app.state.scheduler_manager = scheduler_manager
    app.state.config_manager = config_manager
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client with the test app"""
    return TestClient(test_app)


@pytest.fixture
def sample_events():
    """Sample news events for testing"""
    return [
        {
            "id": "event-1",
            "source": "TechCrunch",
            "title": "AI Breakthrough in Machine Learning",
            "body": "Researchers discover new algorithm that improves accuracy by 20%",
            "published_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "event-2", 
            "source": "Reuters",
            "title": "Global Tech Market Update",
            "body": "Tech stocks show strong performance in Q1",
            "published_at": "2024-01-15T14:45:00Z"
        }
    ]


@pytest.fixture
def invalid_event():
    """Invalid event data for testing error cases"""
    return [
        {
            "id": "event-3",
            "source": "Invalid Source",
            # Missing required fields: title, published_at
        }
    ]


@pytest.fixture
def mock_source_config():
    """Mock source configuration for testing"""
    return {
        "sources": {
            "test_source": {
                "enabled": True,
                "poll_interval": 300,
                "source_type": "mock",
                "adapter_class": "GitHubStatusAdapter",
                "url": "https://api.example.com/status"
            }
        }
    } 