import pytest
from datetime import datetime, timezone, timedelta
from src.models.domain import NewsEvent, NewsType
from src.repositories.news_event_repository import ChromaDBNewsEventRepository, InMemoryNewsEventRepository


class TestChromaDBNewsEventRepository:
    """Test ChromaDB repository functionality"""
    
    @pytest.fixture
    def repository(self, tmp_path):
        """Create a ChromaDB repository for testing"""
        return ChromaDBNewsEventRepository(persist_directory=str(tmp_path / "chromadb"))
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing"""
        now = datetime.now(timezone.utc)
        
        return [
            NewsEvent(
                id="event1",
                source="test_source",
                title="Critical system outage affecting production",
                body="A major system failure has occurred in production environment",
                published_at=now - timedelta(hours=1),  # 1 hour ago
                status="investigating",
                impact_level="critical",
                news_type=NewsType.SERVICE_STATUS,
                url="https://example.com/event1",
                affected_components=["database", "api"],
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=30)
            ),
            NewsEvent(
                id="event2",
                source="test_source",
                title="Security vulnerability discovered",
                body="A critical security vulnerability has been identified in the authentication system",
                published_at=now - timedelta(hours=6),  # 6 hours ago
                status="identified",
                impact_level="major",
                news_type=NewsType.SECURITY_ADVISORY,
                url="https://example.com/event2",
                affected_components=["auth", "login"],
                created_at=now - timedelta(hours=6),
                updated_at=now - timedelta(hours=5)
            ),
            NewsEvent(
                id="event3",
                source="test_source",
                title="Software bug causing data corruption",
                body="A severe bug has been found that can cause data corruption in the storage system",
                published_at=now - timedelta(hours=12),  # 12 hours ago
                status="monitoring",
                impact_level="major",
                news_type=NewsType.SOFTWARE_BUG,
                url="https://example.com/event3",
                affected_components=["storage", "database"],
                created_at=now - timedelta(hours=12),
                updated_at=now - timedelta(hours=10)
            ),
            NewsEvent(
                id="event4",
                source="test_source",
                title="Minor performance degradation",
                body="Users are experiencing slightly slower response times",
                published_at=now - timedelta(hours=24),  # 24 hours ago
                status="resolved",
                impact_level="minor",
                news_type=NewsType.SERVICE_STATUS,
                url="https://example.com/event4",
                affected_components=["api"],
                created_at=now - timedelta(hours=24),
                updated_at=now - timedelta(hours=22),
                resolved_at=now - timedelta(hours=22)
            ),
            NewsEvent(
                id="event5",
                source="test_source",
                title="Old maintenance notification",
                body="Scheduled maintenance completed successfully",
                published_at=now - timedelta(days=3),  # 3 days ago
                status="resolved",
                impact_level="none",
                news_type=NewsType.SERVICE_STATUS,
                url="https://example.com/event5",
                affected_components=["maintenance"],
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(days=2),
                resolved_at=now - timedelta(days=2)
            )
        ]
    
    def test_create_and_retrieve_events(self, repository, sample_events):
        """Test basic create and retrieve functionality"""
        # Create events
        repository.create_events(sample_events)
        
        # Retrieve all events
        retrieved_events = repository.get_all_events()
        
        assert len(retrieved_events) == len(sample_events)
        
        # Check that all events are present
        retrieved_ids = {event.id for event in retrieved_events}
        expected_ids = {event.id for event in sample_events}
        assert retrieved_ids == expected_ids
    
    def test_search_events(self, repository, sample_events):
        """Test semantic search functionality"""
        # Create events
        repository.create_events(sample_events)
        
        # Search for critical events
        results = repository.search_events("critical system outage", limit=10)
        
        assert len(results) > 0
        # Should find event1 which mentions "Critical system outage"
        found_event1 = any(event.id == "event1" for event in results)
        assert found_event1
    

class TestInMemoryNewsEventRepository:
    """Test in-memory repository functionality"""
    
    @pytest.fixture
    def repository(self):
        """Create an in-memory repository for testing"""
        return InMemoryNewsEventRepository()
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing"""
        now = datetime.now(timezone.utc)
        
        return [
            NewsEvent(
                id="event1",
                source="test_source",
                title="Recent event",
                body="This is a recent event",
                published_at=now - timedelta(hours=1),
                status="investigating",
                impact_level="critical",
                news_type=NewsType.SERVICE_STATUS
            ),
            NewsEvent(
                id="event2",
                source="test_source",
                title="Older event",
                body="This is an older event",
                published_at=now - timedelta(hours=24),
                status="resolved",
                impact_level="minor",
                news_type=NewsType.SERVICE_STATUS
            )
        ]
    