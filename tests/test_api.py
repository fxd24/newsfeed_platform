import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.api import routes
from datetime import datetime



@pytest.fixture(autouse=True)
def clear_storage():
    """Clear the events storage before each test to prevent data accumulation"""
    routes.events_storage.clear()
    yield


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


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


def test_health_endpoint(client):
    """Test that the health endpoint returns the expected response"""
    # Make a GET request to the health endpoint
    response = client.get("/health")
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response contains the expected JSON data
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "IT Newsfeed Platform"
    
    # Assert the response has the correct content type
    assert response.headers["content-type"] == "application/json"


def test_health_endpoint_structure(client):
    """Test that the health endpoint response has the correct structure"""
    response = client.get("/health")
    
    # Verify the response is valid JSON
    data = response.json()
    
    # Check that all required fields are present
    required_fields = ["status", "service"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check that the values are strings
    assert isinstance(data["status"], str)
    assert isinstance(data["service"], str)


def test_ingest_events_success(client, sample_events):
    """Test successful ingestion of events"""
    response = client.post("/ingest", json=sample_events)
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response structure
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Successfully stored 2 events"
    
    # Assert the response has the correct content type
    assert response.headers["content-type"] == "application/json"


def test_ingest_events_validation_error(client, invalid_event):
    """Test ingestion with invalid event data"""
    response = client.post("/ingest", json=invalid_event)
    
    # Assert the response status code is 422 Unprocessable Entity
    assert response.status_code == 422
    
    # Assert the response contains error details
    data = response.json()
    assert "detail" in data
    assert "Invalid event format" in data["detail"]


def test_ingest_empty_array(client):
    """Test ingestion of empty array"""
    response = client.post("/ingest", json=[])
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response structure
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Successfully stored 0 events"


def test_ingest_single_event(client):
    """Test ingestion of a single event"""
    single_event = [{
        "id": "single-event",
        "source": "Single Source",
        "title": "Single Event Title",
        "body": "Single event body content",
        "published_at": "2024-01-15T12:00:00Z"
    }]
    
    response = client.post("/ingest", json=single_event)
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response structure
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Successfully stored 1 events"


def test_retrieve_events_empty(client):
    """Test retrieving events when storage is empty"""
    response = client.get("/retrieve")
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response is an empty array
    data = response.json()
    assert data == []
    
    # Assert the response has the correct content type
    assert response.headers["content-type"] == "application/json"


def test_retrieve_events_after_ingest(client, sample_events):
    """Test retrieving events after ingestion"""
    # First, ingest some events
    ingest_response = client.post("/ingest", json=sample_events)
    assert ingest_response.status_code == 200
    
    # Then retrieve all events
    response = client.get("/retrieve")
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Assert the response contains the ingested events
    data = response.json()
    assert len(data) == 2
    
    # Verify the structure of returned events
    for event in data:
        assert "id" in event
        assert "source" in event
        assert "title" in event
        assert "body" in event
        assert "published_at" in event
        
        # Verify data types
        assert isinstance(event["id"], str)
        assert isinstance(event["source"], str)
        assert isinstance(event["title"], str)
        assert isinstance(event["body"], str)
        assert isinstance(event["published_at"], str)  # ISO format string


def test_retrieve_events_persistence(client, sample_events):
    """Test that events persist across multiple retrieve calls"""
    # Ingest events
    client.post("/ingest", json=sample_events)
    
    # Retrieve events multiple times
    response1 = client.get("/retrieve")
    response2 = client.get("/retrieve")
    
    # Both responses should be identical
    assert response1.json() == response2.json()
    assert len(response1.json()) == 2


def test_ingest_events_with_minimal_data(client):
    """Test ingestion with minimal required data"""
    minimal_event = [{
        "id": "minimal-event",
        "source": "Minimal Source",
        "title": "Minimal Title",
        "published_at": "2024-01-15T12:00:00Z"
        # body is optional, so we omit it
    }]
    
    response = client.post("/ingest", json=minimal_event)
    
    # Assert the response status code is 200 OK
    assert response.status_code == 200
    
    # Verify the event was stored correctly
    retrieve_response = client.get("/retrieve")
    events = retrieve_response.json()
    
    # Find our event
    stored_event = next((e for e in events if e["id"] == "minimal-event"), None)
    assert stored_event is not None
    assert stored_event["body"] == ""  # Default value for body


def test_ingest_events_with_malformed_datetime(client):
    """Test ingestion with malformed datetime"""
    malformed_event = [{
        "id": "malformed-event",
        "source": "Test Source",
        "title": "Test Title",
        "body": "Test body",
        "published_at": "invalid-datetime-format"
    }]
    
    response = client.post("/ingest", json=malformed_event)
    
    # Assert the response status code is 422 Unprocessable Entity
    assert response.status_code == 422
    
    # Assert the response contains error details
    data = response.json()
    assert "detail" in data
    assert "Invalid event format" in data["detail"] 