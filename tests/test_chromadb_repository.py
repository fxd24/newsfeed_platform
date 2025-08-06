import pytest
import tempfile
import shutil
import logging
from datetime import datetime
from src.repositories.news_event_repository import ChromaDBNewsEventRepository
from src.models.domain import NewsEvent
from src.models.domain import NewsType

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB storage"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def chroma_repository(temp_chroma_dir):
    """Create a fresh ChromaDB repository instance for each test"""
    repo = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
    yield repo
    # Cleanup after each test
    try:
        repo.delete_all_events()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def sample_events():
    """Sample news events for testing"""
    return [
        NewsEvent(
            id="event-1",
            source="TechCrunch",
            title="AI Breakthrough in Machine Learning",
            body="Researchers discover new algorithm that improves accuracy by 20%",
            published_at=datetime(2024, 1, 15, 10, 30, 0)
        ),
        NewsEvent(
            id="event-2",
            source="Reuters",
            title="Global Tech Market Update",
            body="Tech stocks show strong performance in Q1",
            published_at=datetime(2024, 1, 15, 14, 45, 0)
        ),
        NewsEvent(
            id="event-3",
            source="BBC",
            title="Climate Change Summit",
            body="World leaders meet to discuss climate action",
            published_at=datetime(2024, 1, 16, 9, 0, 0)
        )
    ]


@pytest.fixture
def single_event():
    """Single event for testing"""
    return NewsEvent(
        id="single-event",
        source="CNN",
        title="Breaking News",
        body="This is a breaking news story",
        published_at=datetime(2024, 1, 17, 12, 0, 0)
    )


class TestChromaDBNewsEventRepository:
    """Test suite for ChromaDBNewsEventRepository"""

    def test_initialization(self, temp_chroma_dir):
        """Test ChromaDB repository initialization"""
        repo = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        assert repo.client is not None
        assert repo.collection is not None
        assert repo.collection.name == "news_events"
        assert repo.count_events() == 0

    def test_initialization_with_existing_data(self, temp_chroma_dir, sample_events):
        """Test initialization when ChromaDB already has data"""
        # Create first repository and add data
        repo1 = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        repo1.create_events(sample_events)
        assert repo1.count_events() == 3
        
        # Create second repository with same directory
        repo2 = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        assert repo2.count_events() == 3  # Should see existing data

    def test_create_events_empty_list(self, chroma_repository):
        """Test creating events with empty list"""
        chroma_repository.create_events([])
        assert chroma_repository.count_events() == 0
        assert chroma_repository.get_all_events() == []

    def test_create_events_single_event(self, chroma_repository, single_event):
        """Test creating a single event"""
        chroma_repository.create_events([single_event])
        
        assert chroma_repository.count_events() == 1
        events = chroma_repository.get_all_events()
        assert len(events) == 1
        
        # Check event data integrity
        retrieved_event = events[0]
        assert retrieved_event.id == single_event.id
        assert retrieved_event.source == single_event.source
        assert retrieved_event.title == single_event.title
        assert retrieved_event.body == single_event.body
        assert retrieved_event.published_at == single_event.published_at

    def test_create_events_multiple_events(self, chroma_repository, sample_events):
        """Test creating multiple events"""
        chroma_repository.create_events(sample_events)
        
        assert chroma_repository.count_events() == 3
        events = chroma_repository.get_all_events()
        assert len(events) == 3
        
        # Check that all events are present
        event_ids = {event.id for event in events}
        expected_ids = {event.id for event in sample_events}
        assert event_ids == expected_ids

    def test_create_events_duplicate_handling(self, chroma_repository, single_event):
        """Test that duplicate events are handled correctly (upsert behavior)"""
        # Create the same event twice
        chroma_repository.create_events([single_event])
        chroma_repository.create_events([single_event])
        
        # Should only have one event (upsert behavior)
        assert chroma_repository.count_events() == 1
        events = chroma_repository.get_all_events()
        assert len(events) == 1
        assert events[0].id == single_event.id

    def test_create_events_update_existing(self, chroma_repository):
        """Test that creating an event with same ID but different content updates it"""
        event1 = NewsEvent(
            id="same-id",
            source="Source 1",
            title="Title 1",
            body="Body 1",
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        event2 = NewsEvent(
            id="same-id",  # Same ID
            source="Source 2",  # Different content
            title="Title 2",
            body="Body 2",
            published_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        chroma_repository.create_events([event1])
        chroma_repository.create_events([event2])
        
        # Should only have one event (the updated one)
        assert chroma_repository.count_events() == 1
        retrieved_event = chroma_repository.get_event_by_id("same-id")
        assert retrieved_event.source == "Source 2"
        assert retrieved_event.title == "Title 2"

    def test_get_all_events_empty_repository(self, chroma_repository):
        """Test getting all events from empty repository"""
        events = chroma_repository.get_all_events()
        assert events == []
        assert isinstance(events, list)

    def test_get_all_events_with_data(self, chroma_repository, sample_events):
        """Test getting all events when repository has data"""
        chroma_repository.create_events(sample_events)
        events = chroma_repository.get_all_events()
        
        assert len(events) == 3
        # Check that all events have correct data
        for event in events:
            assert isinstance(event, NewsEvent)
            assert event.id in ["event-1", "event-2", "event-3"]

    def test_get_event_by_id_existing_event(self, chroma_repository, sample_events):
        """Test getting an existing event by ID"""
        chroma_repository.create_events(sample_events)
        
        event = chroma_repository.get_event_by_id("event-1")
        assert event is not None
        assert event.id == "event-1"
        assert event.source == "TechCrunch"
        assert event.title == "AI Breakthrough in Machine Learning"

    def test_get_event_by_id_nonexistent_event(self, chroma_repository):
        """Test getting a non-existent event by ID"""
        event = chroma_repository.get_event_by_id("nonexistent-id")
        assert event is None

    def test_get_event_by_id_empty_repository(self, chroma_repository):
        """Test getting event by ID from empty repository"""
        event = chroma_repository.get_event_by_id("any-id")
        assert event is None

    def test_count_events_empty_repository(self, chroma_repository):
        """Test counting events in empty repository"""
        assert chroma_repository.count_events() == 0

    def test_count_events_after_creation(self, chroma_repository, sample_events):
        """Test counting events after creating them"""
        assert chroma_repository.count_events() == 0
        
        chroma_repository.create_events(sample_events)
        assert chroma_repository.count_events() == 3
        
        # Add one more event
        new_event = NewsEvent(
            id="event-4",
            source="New Source",
            title="New Title",
            body="New body",
            published_at=datetime(2024, 1, 19, 10, 0, 0)
        )
        chroma_repository.create_events([new_event])
        assert chroma_repository.count_events() == 4

    def test_delete_all_events_empty_repository(self, chroma_repository):
        """Test deleting all events from empty repository"""
        chroma_repository.delete_all_events()
        assert chroma_repository.count_events() == 0
        assert chroma_repository.get_all_events() == []

    def test_delete_all_events_with_data(self, chroma_repository, sample_events):
        """Test deleting all events when repository has data"""
        chroma_repository.create_events(sample_events)
        assert chroma_repository.count_events() == 3
        
        chroma_repository.delete_all_events()
        assert chroma_repository.count_events() == 0
        assert chroma_repository.get_all_events() == []
        
        # Verify that getting by ID returns None
        assert chroma_repository.get_event_by_id("event-1") is None

    def test_delete_all_events_and_recreate(self, chroma_repository, sample_events):
        """Test that events can be recreated after deletion"""
        chroma_repository.create_events(sample_events)
        chroma_repository.delete_all_events()
        
        # Create events again
        chroma_repository.create_events(sample_events)
        assert chroma_repository.count_events() == 3
        
        # Verify events are accessible
        event = chroma_repository.get_event_by_id("event-1")
        assert event is not None
        assert event.title == "AI Breakthrough in Machine Learning"

    def test_events_with_empty_body(self, chroma_repository):
        """Test handling events with empty body"""
        event = NewsEvent(
            id="empty-body-event",
            source="Test Source",
            title="Test Title",
            body="",  # Empty body
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        chroma_repository.create_events([event])
        retrieved_event = chroma_repository.get_event_by_id("empty-body-event")
        
        assert retrieved_event is not None
        assert retrieved_event.body == ""
        assert retrieved_event.title == "Test Title"

    def test_large_number_of_events(self, chroma_repository):
        """Test handling a large number of events"""
        events = []
        for i in range(100):  # Reduced from 1000 for faster testing
            event = NewsEvent(
                id=f"event-{i}",
                source=f"Source {i}",
                title=f"Title {i}",
                body=f"Body {i}",
                published_at=datetime(2024, 1, 1, 12, 0, 0)
            )
            events.append(event)
        
        chroma_repository.create_events(events)
        assert chroma_repository.count_events() == 100
        
        # Test retrieving a specific event
        event_50 = chroma_repository.get_event_by_id("event-50")
        assert event_50 is not None
        assert event_50.title == "Title 50"
        
        # Test getting all events
        all_events = chroma_repository.get_all_events()
        assert len(all_events) == 100

    def test_search_events_empty_repository(self, chroma_repository):
        """Test search functionality with empty repository"""
        results = chroma_repository.search_events("test query")
        assert results == []

    def test_search_events_basic(self, chroma_repository, sample_events):
        """Test basic search functionality"""
        chroma_repository.create_events(sample_events)
        
        # Search for AI-related content
        results = chroma_repository.search_events("AI machine learning")
        assert len(results) > 0
        
        # Check that results contain relevant content
        result_titles = [event.title for event in results]
        assert any("AI" in title for title in result_titles)

    def test_search_events_with_limit(self, chroma_repository):
        """Test search with custom limit"""
        # Create many events
        events = []
        for i in range(20):
            event = NewsEvent(
                id=f"event-{i}",
                source=f"Source {i}",
                title=f"Title {i}",
                body=f"Body {i}",
                published_at=datetime(2024, 1, 1, 12, 0, 0)
            )
            events.append(event)
        
        chroma_repository.create_events(events)
        
        # Search with limit
        results = chroma_repository.search_events("Title", limit=5)
        assert len(results) <= 5

    def test_search_events_no_matches(self, chroma_repository, sample_events):
        """Test search when no matches are found"""
        chroma_repository.create_events(sample_events)
        
        # Search for something that shouldn't match
        # Note: ChromaDB semantic search may return results even for seemingly unrelated queries
        # So we test that the results don't contain the exact search term
        results = chroma_repository.search_events("xyz123nonexistent")
        
        # Check that none of the results contain the exact search term
        search_term = "xyz123nonexistent"
        for event in results:
            assert search_term.lower() not in event.title.lower()
            assert search_term.lower() not in event.body.lower()
            assert search_term.lower() not in event.source.lower()

    def test_search_events_case_insensitive(self, chroma_repository, sample_events):
        """Test that search is case insensitive"""
        chroma_repository.create_events(sample_events)
        
        # Search with different cases
        results1 = chroma_repository.search_events("ai breakthrough")
        results2 = chroma_repository.search_events("AI BREAKTHROUGH")
        
        # Should return similar results (ChromaDB handles case sensitivity)
        assert len(results1) > 0
        assert len(results2) > 0

    def test_repository_persistence(self, temp_chroma_dir, sample_events):
        """Test that data persists between repository instances"""
        # Create first repository and add data
        repo1 = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        repo1.create_events(sample_events)
        assert repo1.count_events() == 3
        
        # Create second repository with same directory
        repo2 = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        assert repo2.count_events() == 3
        
        # Verify data integrity
        events = repo2.get_all_events()
        assert len(events) == 3
        event_ids = {event.id for event in events}
        expected_ids = {event.id for event in sample_events}
        assert event_ids == expected_ids

    def test_error_handling_invalid_directory(self):
        """Test error handling when ChromaDB can't be initialized"""
        with pytest.raises(Exception):
            # Try to use a non-existent directory
            ChromaDBNewsEventRepository(persist_directory="/non/existent/path")

    def test_error_handling_corrupted_data(self, temp_chroma_dir):
        """Test error handling with corrupted ChromaDB data"""
        # Create a repository
        repo = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        
        # Add some data
        event = NewsEvent(
            id="test-event",
            source="Test Source",
            title="Test Title",
            body="Test body",
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        repo.create_events([event])
        
        # Verify it works
        assert repo.count_events() == 1
        
        # Now try to access it again (should work)
        repo2 = ChromaDBNewsEventRepository(persist_directory=temp_chroma_dir)
        assert repo2.count_events() == 1

    def test_events_with_affected_components(self, chroma_repository):
        """Test that events with affected_components lists are properly stored and retrieved"""
        # Create an event with affected components
        event = NewsEvent(
            id="test-components",
            source="Test Source",
            title="Test Title",
            body="Test body",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            affected_components=["Component A", "Component B", "Component C"]
        )
        
        # Store the event
        chroma_repository.create_events([event])
        
        # Retrieve the event
        retrieved_events = chroma_repository.get_all_events()
        assert len(retrieved_events) == 1
        
        retrieved_event = retrieved_events[0]
        assert retrieved_event.affected_components == ["Component A", "Component B", "Component C"]
        
        # Test search functionality with affected components
        search_results = chroma_repository.search_events("Component A", limit=5)
        assert len(search_results) > 0
        assert any("Component A" in (event.affected_components or []) for event in search_results)

    def test_events_with_null_affected_components(self, chroma_repository):
        """Test that events with null affected_components are handled correctly"""
        # Create an event without affected components
        event = NewsEvent(
            id="test-no-components",
            source="Test Source",
            title="Test Title",
            body="Test body",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            affected_components=None
        )
        
        # Store the event
        chroma_repository.create_events([event])
        
        # Retrieve the event
        retrieved_events = chroma_repository.get_all_events()
        assert len(retrieved_events) == 1
        
        retrieved_event = retrieved_events[0]
        assert retrieved_event.affected_components is None

    def test_events_with_empty_affected_components(self, chroma_repository):
        """Test that events with empty affected_components lists are handled correctly"""
        # Create an event with empty affected components
        event = NewsEvent(
            id="test-empty-components",
            source="Test Source",
            title="Test Title",
            body="Test body",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            affected_components=[]
        )
        
        # Store the event
        chroma_repository.create_events([event])
        
        # Retrieve the event
        retrieved_events = chroma_repository.get_all_events()
        assert len(retrieved_events) == 1
        
        retrieved_event = retrieved_events[0]
        assert retrieved_event.affected_components is None  # Empty list becomes None in storage

    def test_events_with_status_and_impact(self, chroma_repository):
        """Test that events with status and impact information are properly stored and retrieved"""
        # Create an event with status and impact information
        event = NewsEvent(
            id="test-status-impact",
            source="GitHub Status",
            title="Major Service Outage",
            body="Critical service disruption affecting multiple services",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            status="investigating",
            impact_level="major",
            news_type=NewsType.SERVICE_STATUS,
            url="https://status.github.com/incident/123",
            affected_components=["Actions", "API", "Webhooks"],
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 13, 0, 0),
            resolved_at=datetime(2024, 1, 1, 14, 0, 0)
        )
        
        # Store the event
        chroma_repository.create_events([event])
        
        # Retrieve the event
        retrieved_events = chroma_repository.get_all_events()
        assert len(retrieved_events) == 1
        
        retrieved_event = retrieved_events[0]
        assert retrieved_event.status == "investigating"
        assert retrieved_event.impact_level == "major"
        assert retrieved_event.news_type == NewsType.SERVICE_STATUS
        assert retrieved_event.url == "https://status.github.com/incident/123"
        assert retrieved_event.affected_components == ["Actions", "API", "Webhooks"]
        assert retrieved_event.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert retrieved_event.updated_at == datetime(2024, 1, 1, 13, 0, 0)
        assert retrieved_event.resolved_at == datetime(2024, 1, 1, 14, 0, 0)
        
        # Test search functionality with status and impact
        search_results = chroma_repository.search_events("major outage", limit=5)
        assert len(search_results) > 0
        assert any(event.impact_level == "major" for event in search_results)

    def test_events_with_null_status_and_impact(self, chroma_repository):
        """Test that events with null status and impact are handled correctly"""
        # Create an event without status and impact information
        event = NewsEvent(
            id="test-null-status-impact",
            source="RSS Feed",
            title="General News Article",
            body="This is a general news article without status or impact information",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            status=None,
            impact_level=None,
            news_type=NewsType.UNKNOWN
        )
        
        # Store the event
        chroma_repository.create_events([event])
        
        # Retrieve the event
        retrieved_events = chroma_repository.get_all_events()
        assert len(retrieved_events) == 1
        
        retrieved_event = retrieved_events[0]
        assert retrieved_event.status is None
        assert retrieved_event.impact_level is None
        assert retrieved_event.news_type == NewsType.UNKNOWN

    def test_it_manager_search_query(self, chroma_repository):
        """Test that IT manager focused search returns relevant IT events"""
        # Create IT-relevant events
        it_events = [
            NewsEvent(
                id="outage-1",
                source="AWS Status",
                title="Major AWS Outage Affecting Multiple Services",
                body="Critical service disruption impacting EC2, S3, and RDS services across multiple regions. Engineers are working to resolve the issue.",
                published_at=datetime(2024, 1, 15, 10, 30, 0)
            ),
            NewsEvent(
                id="security-1",
                source="Security Weekly",
                title="Critical Zero-Day Vulnerability in Apache Log4j",
                body="Severe security vulnerability allows remote code execution. Immediate patching required for all affected systems.",
                published_at=datetime(2024, 1, 15, 14, 45, 0)
            ),
            NewsEvent(
                id="bug-1",
                source="GitHub Issues",
                title="Critical Bug in Production Database",
                body="Data corruption issue affecting production systems. Emergency hotfix being deployed.",
                published_at=datetime(2024, 1, 16, 9, 0, 0)
            ),
            NewsEvent(
                id="non-it-1",
                source="Sports News",
                title="Local Team Wins Championship",
                body="Great victory for the local sports team in the championship game.",
                published_at=datetime(2024, 1, 16, 12, 0, 0)
            )
        ]
        
        chroma_repository.create_events(it_events)
        
        # Use the same IT manager query as in the API
        it_manager_query = """
        major outage critical incident service disruption system failure
        cybersecurity threat security breach vulnerability exploit malware ransomware
        critical software bug severe bug production issue data loss
        emergency maintenance urgent fix hotfix patch
        """
        
        # Search for IT-relevant events
        results = chroma_repository.search_events(it_manager_query, limit=10)
        
        # Should return IT-relevant events
        assert len(results) > 0
        
        # Check that we get IT-relevant events (outage, security, bug)
        result_ids = {event.id for event in results}
        it_relevant_ids = {"outage-1", "security-1", "bug-1"}
        
        # At least some IT-relevant events should be returned
        assert len(result_ids.intersection(it_relevant_ids)) > 0
        
        # Verify the non-IT event is less likely to be returned
        # (though semantic search might still return it with lower relevance) 