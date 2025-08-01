import pytest
import tempfile
import shutil
import os
from fastapi.testclient import TestClient
from src.main import app
from src.repositories.news_event_repository import InMemoryNewsEventRepository, ChromaDBNewsEventRepository


class BaseAPITestCase:
    """Base test class with common test methods"""
    
    def setup_repository(self):
        """Set up the repository for testing - to be implemented by subclasses"""
        raise NotImplementedError
    
    def teardown_repository(self):
        """Clean up the repository after testing - to be implemented by subclasses"""
        raise NotImplementedError
    
    def setup_app_state(self):
        """Set up the app state with required components"""
        from src.services import IngestionService
        from src.sources.factory import SourceManager
        from src.scheduler import SchedulerManager
        from src.config import ConfigManager
        
        # Create components
        self.repository = self.create_repository()
        self.ingestion_service = IngestionService(self.repository)
        self.source_manager = SourceManager()
        self.scheduler_manager = SchedulerManager(self.source_manager, self.ingestion_service)
        self.config_manager = ConfigManager()
        
        # Set up app state
        app.state.repository = self.repository
        app.state.ingestion_service = self.ingestion_service
        app.state.source_manager = self.source_manager
        app.state.scheduler_manager = self.scheduler_manager
        app.state.config_manager = self.config_manager
    
    def create_repository(self):
        """Create repository - to be implemented by subclasses"""
        raise NotImplementedError
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        self.setup_app_state()
        self.setup_repository()
        yield
        self.teardown_repository()
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_events(self):
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
    def invalid_event(self):
        """Invalid event data for testing error cases"""
        return [
            {
                "id": "event-3",
                "source": "Invalid Source",
                # Missing required fields: title, published_at
            }
        ]
    
    def test_health_endpoint(self, client):
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
    
    def test_health_endpoint_structure(self, client):
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
    
    def test_ingest_events_success(self, client, sample_events):
        """Test successful ingestion of events"""
        response = client.post("/ingest", json=sample_events)
        
        # Assert the response status code is 200 OK
        assert response.status_code == 200
        
        # Assert the response structure
        data = response.json()
        assert data["status"] == "ok"
        assert "Successfully ingested 2 events" in data["message"]
        
        # Assert the response has the correct content type
        assert response.headers["content-type"] == "application/json"
    
    def test_ingest_events_validation_error(self, client, invalid_event):
        """Test ingestion with invalid event data"""
        response = client.post("/ingest", json=invalid_event)
        
        # Assert the response status code is 422 Unprocessable Entity
        assert response.status_code == 422
        
        # Assert the response contains error details
        data = response.json()
        assert "detail" in data
        assert "Invalid event format" in data["detail"]
    
    def test_ingest_empty_array(self, client):
        """Test ingestion of empty array"""
        response = client.post("/ingest", json=[])
        
        # Assert the response status code is 200 OK
        assert response.status_code == 200
        
        # Assert the response structure
        data = response.json()
        assert data["status"] == "ok"
        assert "Successfully ingested 0 events" in data["message"]
    
    def test_ingest_single_event(self, client):
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
        assert "Successfully ingested 1 events" in data["message"]
    
    def test_retrieve_events_empty(self, client):
        """Test retrieving events when storage is empty"""
        response = client.get("/retrieve")
        
        # Assert the response status code is 200 OK
        assert response.status_code == 200
        
        # Assert the response is an empty array
        data = response.json()
        assert data == []
        
        # Assert the response has the correct content type
        assert response.headers["content-type"] == "application/json"
    
    def test_retrieve_events_after_ingest(self, client, sample_events):
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
    
    def test_retrieve_events_persistence(self, client, sample_events):
        """Test that events persist across multiple retrieve calls"""
        # Ingest events
        client.post("/ingest", json=sample_events)
        
        # Retrieve events multiple times
        response1 = client.get("/retrieve")
        response2 = client.get("/retrieve")
        
        # Both responses should be identical
        assert response1.json() == response2.json()
        assert len(response1.json()) == 2
    
    def test_ingest_events_with_minimal_data(self, client):
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
    
    def test_ingest_events_with_malformed_datetime(self, client):
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


class TestAPIWithInMemoryRepository(BaseAPITestCase):
    """Test API with InMemoryNewsEventRepository"""
    
    def create_repository(self):
        """Create in-memory repository for testing"""
        return InMemoryNewsEventRepository()
    
    def setup_repository(self):
        """Set up the in-memory repository for testing"""
        # Repository is already created in setup_app_state # TODO
        pass
    
    def teardown_repository(self):
        """Clean up the in-memory repository after testing"""
        if hasattr(self, 'repository') and self.repository:
            self.repository.delete_all_events()


class TestAPIWithChromaDBRepository(BaseAPITestCase):
    """Test API with ChromaDBNewsEventRepository"""
    
    def create_repository(self):
        """Create ChromaDB repository for testing"""
        # Create a temporary directory for ChromaDB
        self.temp_dir = tempfile.mkdtemp(prefix="test_chromadb_")
        return ChromaDBNewsEventRepository(persist_directory=self.temp_dir)
    
    def setup_repository(self):
        """Set up the ChromaDB repository for testing"""
        # Repository is already created in setup_app_state
        pass
    
    def teardown_repository(self):
        """Clean up the ChromaDB repository after testing"""
        if hasattr(self, 'repository') and self.repository:
            self.repository.delete_all_events()
        
        # Remove the temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


# # Alternative approach using pytest parametrization
# @pytest.mark.parametrize("repository_type", ["memory", "chromadb"])
# class TestAPIParametrized:
#     """Parametrized tests for both repository types"""
    
#     @pytest.fixture(autouse=True)
#     def setup_repository(self, repository_type):
#         """Set up the repository based on the parameter"""
#         if repository_type == "chromadb":
#             # Create a temporary directory for ChromaDB
#             self.temp_dir = tempfile.mkdtemp(prefix="test_chromadb_")
#             app.state.repository = ChromaDBNewsEventRepository(persist_directory=self.temp_dir)
#         else:
#             app.state.repository = InMemoryNewsEventRepository()
        
#         yield
        
#         # Cleanup
#         if hasattr(app.state, 'repository') and app.state.repository:
#             app.state.repository.delete_all_events()
        
#         # Remove temporary directory for ChromaDB
#         if repository_type == "chromadb" and hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
#             shutil.rmtree(self.temp_dir)
    
#     @pytest.fixture
#     def client(self):
#         """Create a test client for the FastAPI app"""
#         return TestClient(app)
    
#     @pytest.fixture
#     def sample_events(self):
#         """Sample news events for testing"""
#         return [
#             {
#                 "id": "event-1",
#                 "source": "TechCrunch",
#                 "title": "AI Breakthrough in Machine Learning",
#                 "body": "Researchers discover new algorithm that improves accuracy by 20%",
#                 "published_at": "2024-01-15T10:30:00Z"
#             },
#             {
#                 "id": "event-2", 
#                 "source": "Reuters",
#                 "title": "Global Tech Market Update",
#                 "body": "Tech stocks show strong performance in Q1",
#                 "published_at": "2024-01-15T14:45:00Z"
#             }
#         ]
    
#     def test_ingest_and_retrieve(self, client, sample_events, repository_type):
#         """Test basic ingest and retrieve functionality"""
#         # Ingest events
#         ingest_response = client.post("/ingest", json=sample_events)
#         assert ingest_response.status_code == 200
        
#         # Retrieve events
#         retrieve_response = client.get("/retrieve")
#         assert retrieve_response.status_code == 200
        
#         # Verify data
#         events = retrieve_response.json()
#         assert len(events) == 2
        
#         # Log which repository type was used
#         print(f"\nTested with {repository_type} repository")
    
#     def test_health_endpoint(self, client, repository_type):
#         """Test health endpoint"""
#         response = client.get("/health")
#         assert response.status_code == 200
#         data = response.json()
#         assert data["status"] == "healthy"
#         print(f"\nHealth test with {repository_type} repository")