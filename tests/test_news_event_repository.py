import pytest
from datetime import datetime
from src.repositories.news_event_repository import InMemoryNewsEventRepository
from src.models.domain import NewsEvent

# TODO name better the file and check similarly with chromadb tests

@pytest.fixture
def repository():
    """Create a fresh repository instance for each test"""
    return InMemoryNewsEventRepository()


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


class TestInMemoryNewsEventRepository:
    """Test suite for InMemoryNewsEventRepository"""

    def test_create_events_empty_list(self, repository):
        """Test creating events with empty list"""
        repository.create_events([])
        assert repository.count_events() == 0
        assert repository.get_all_events() == []

    def test_create_events_single_event(self, repository, single_event):
        """Test creating a single event"""
        repository.create_events([single_event])
        
        assert repository.count_events() == 1
        events = repository.get_all_events()
        assert len(events) == 1
        assert events[0] == single_event

    def test_create_events_multiple_events(self, repository, sample_events):
        """Test creating multiple events"""
        repository.create_events(sample_events)
        
        assert repository.count_events() == 3
        events = repository.get_all_events()
        assert len(events) == 3
        
        # Check that all events are present
        event_ids = {event.id for event in events}
        expected_ids = {event.id for event in sample_events}
        assert event_ids == expected_ids

    def test_create_events_duplicate_handling(self, repository, single_event):
        """Test that duplicate events are handled correctly"""
        # Create the same event twice
        repository.create_events([single_event])
        repository.create_events([single_event])
        
        # Should only have one event
        assert repository.count_events() == 1
        events = repository.get_all_events()
        assert len(events) == 1
        assert events[0] == single_event

    def test_create_events_mixed_duplicates(self, repository, sample_events):
        """Test creating events with some duplicates"""
        # Create initial events
        repository.create_events(sample_events)
        initial_count = repository.count_events()
        
        # Create a mix of new and duplicate events
        new_event = NewsEvent(
            id="new-event",
            source="New Source",
            title="New Title",
            body="New body",
            published_at=datetime(2024, 1, 18, 15, 0, 0)
        )
        mixed_events = [sample_events[0], new_event]  # First is duplicate, second is new
        
        repository.create_events(mixed_events)
        
        # Should have one more event (the new one)
        assert repository.count_events() == initial_count + 1
        
        # Check that the new event is present
        retrieved_event = repository.get_event_by_id("new-event")
        assert retrieved_event == new_event

    def test_get_all_events_empty_repository(self, repository):
        """Test getting all events from empty repository"""
        events = repository.get_all_events()
        assert events == []
        assert isinstance(events, list)

    def test_get_all_events_returns_copy(self, repository, sample_events):
        """Test that get_all_events returns a copy, not the original list"""
        repository.create_events(sample_events)
        
        events1 = repository.get_all_events()
        events2 = repository.get_all_events()
        
        # Modifying one should not affect the other
        events1.append("not an event")
        assert len(events1) == len(events2) + 1
        assert len(repository.get_all_events()) == len(sample_events)

    def test_get_event_by_id_existing_event(self, repository, sample_events):
        """Test getting an existing event by ID"""
        repository.create_events(sample_events)
        
        event = repository.get_event_by_id("event-1")
        assert event is not None
        assert event.id == "event-1"
        assert event.source == "TechCrunch"
        assert event.title == "AI Breakthrough in Machine Learning"

    def test_get_event_by_id_nonexistent_event(self, repository):
        """Test getting a non-existent event by ID"""
        event = repository.get_event_by_id("nonexistent-id")
        assert event is None

    def test_get_event_by_id_empty_repository(self, repository):
        """Test getting event by ID from empty repository"""
        event = repository.get_event_by_id("any-id")
        assert event is None

    def test_count_events_empty_repository(self, repository):
        """Test counting events in empty repository"""
        assert repository.count_events() == 0

    def test_count_events_after_creation(self, repository, sample_events):
        """Test counting events after creating them"""
        assert repository.count_events() == 0
        
        repository.create_events(sample_events)
        assert repository.count_events() == 3
        
        # Add one more event
        new_event = NewsEvent(
            id="event-4",
            source="New Source",
            title="New Title",
            body="New body",
            published_at=datetime(2024, 1, 19, 10, 0, 0)
        )
        repository.create_events([new_event])
        assert repository.count_events() == 4

    def test_count_events_after_duplicates(self, repository, single_event):
        """Test counting events after adding duplicates"""
        repository.create_events([single_event])
        assert repository.count_events() == 1
        
        # Add the same event again
        repository.create_events([single_event])
        assert repository.count_events() == 1  # Should not increase

    def test_delete_all_events_empty_repository(self, repository):
        """Test deleting all events from empty repository"""
        repository.delete_all_events()
        assert repository.count_events() == 0
        assert repository.get_all_events() == []

    def test_delete_all_events_with_data(self, repository, sample_events):
        """Test deleting all events when repository has data"""
        repository.create_events(sample_events)
        assert repository.count_events() == 3
        
        repository.delete_all_events()
        assert repository.count_events() == 0
        assert repository.get_all_events() == []
        
        # Verify that getting by ID returns None
        assert repository.get_event_by_id("event-1") is None

    def test_delete_all_events_and_recreate(self, repository, sample_events):
        """Test that events can be recreated after deletion"""
        repository.create_events(sample_events)
        repository.delete_all_events()
        
        # Create events again
        repository.create_events(sample_events)
        assert repository.count_events() == 3
        
        # Verify events are accessible
        event = repository.get_event_by_id("event-1")
        assert event is not None
        assert event.title == "AI Breakthrough in Machine Learning"

    def test_repository_isolation(self):
        """Test that different repository instances are isolated"""
        repo1 = InMemoryNewsEventRepository()
        repo2 = InMemoryNewsEventRepository()
        
        event1 = NewsEvent(
            id="event-1",
            source="Source 1",
            title="Title 1",
            body="Body 1",
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        event2 = NewsEvent(
            id="event-2",
            source="Source 2",
            title="Title 2",
            body="Body 2",
            published_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        repo1.create_events([event1])
        repo2.create_events([event2])
        
        assert repo1.count_events() == 1
        assert repo2.count_events() == 1
        
        assert repo1.get_event_by_id("event-1") is not None
        assert repo1.get_event_by_id("event-2") is None
        
        assert repo2.get_event_by_id("event-1") is None
        assert repo2.get_event_by_id("event-2") is not None

    def test_events_with_empty_body(self, repository):
        """Test handling events with empty body"""
        event = NewsEvent(
            id="empty-body-event",
            source="Test Source",
            title="Test Title",
            body="",  # Empty body
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        repository.create_events([event])
        retrieved_event = repository.get_event_by_id("empty-body-event")
        
        assert retrieved_event is not None
        assert retrieved_event.body == ""
        assert retrieved_event.title == "Test Title"

    def test_events_with_same_id_different_content(self, repository):
        """Test that events with same ID but different content are handled correctly"""
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
        
        repository.create_events([event1])
        repository.create_events([event2])
        
        # Should only have one event (the first one)
        assert repository.count_events() == 1
        retrieved_event = repository.get_event_by_id("same-id")
        assert retrieved_event == event1  # Should be the first event, not the second

    def test_large_number_of_events(self, repository):
        """Test handling a large number of events"""
        events = []
        for i in range(1000):
            event = NewsEvent(
                id=f"event-{i}",
                source=f"Source {i}",
                title=f"Title {i}",
                body=f"Body {i}",
                published_at=datetime(2024, 1, 1, 12, 0, 0)
            )
            events.append(event)
        
        repository.create_events(events)
        assert repository.count_events() == 1000
        
        # Test retrieving a specific event
        event_500 = repository.get_event_by_id("event-500")
        assert event_500 is not None
        assert event_500.title == "Title 500"
        
        # Test getting all events
        all_events = repository.get_all_events()
        assert len(all_events) == 1000 