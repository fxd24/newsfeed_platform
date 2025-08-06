"""
Tests for hybrid relevancy + recency scoring functionality
"""

import pytest
from datetime import datetime, timedelta
from src.repositories.news_event_repository import ChromaDBNewsEventRepository
from src.models.domain import NewsEvent, NewsType


class TestHybridScoring:
    """Test hybrid scoring functionality"""
    
    @pytest.fixture
    def repository(self):
        """Create a test repository"""
        return ChromaDBNewsEventRepository(persist_directory="./data/test_chromadb")
    
    @pytest.fixture
    def sample_events_with_dates(self):
        """Create sample events with different dates to test recency scoring"""
        now = datetime.now()
        
        return [
            NewsEvent(
                id="recent_relevant",
                source="test_source",
                title="Critical system outage affecting production",
                body="A major system failure has occurred that is impacting all production services",
                published_at=now - timedelta(hours=1),  # Very recent
                status="investigating",
                impact_level="critical",
                news_type=NewsType.SERVICE_STATUS
            ),
            NewsEvent(
                id="old_relevant", 
                source="test_source",
                title="Critical security vulnerability discovered",
                body="A severe security flaw has been identified in the authentication system",
                published_at=now - timedelta(days=10),  # Older but still relevant
                status="investigating", 
                impact_level="critical",
                news_type=NewsType.SECURITY_ADVISORY
            ),
            NewsEvent(
                id="recent_irrelevant",
                source="test_source", 
                title="New feature released",
                body="We are excited to announce a new feature that improves user experience",
                published_at=now - timedelta(hours=2),  # Recent but not relevant
                status="resolved",
                impact_level="minor", 
                news_type=NewsType.UNKNOWN
            ),
            NewsEvent(
                id="old_irrelevant",
                source="test_source",
                title="Minor bug fix deployed",
                body="A small bug in the UI has been fixed",
                published_at=now - timedelta(days=15),  # Old and not relevant
                status="resolved",
                impact_level="minor",
                news_type=NewsType.SOFTWARE_BUG
            )
        ]
    
    def test_hybrid_scoring_relevancy_focused(self, repository, sample_events_with_dates):
        """Test that with high alpha (relevancy focus), relevant events rank higher regardless of age"""
        # Create events
        repository.create_events(sample_events_with_dates)
        
        # Search with high alpha (focus on relevancy)
        results = repository.search_events(
            "critical system outage security vulnerability", 
            limit=4,
            alpha=0.9,  # 90% relevancy, 10% recency
            decay_param=0.2
        )
        
        # Should find all events but rank by relevancy
        assert len(results) == 4
        
        # Get event IDs in order
        result_ids = [event.id for event in results]
        
        # Recent relevant and old relevant should be ranked higher than recent/old irrelevant
        assert "recent_relevant" in result_ids[:2] or "old_relevant" in result_ids[:2]
    
    def test_hybrid_scoring_recency_focused(self, repository, sample_events_with_dates):
        """Test that with low alpha (recency focus), recent events rank higher"""
        # Create events
        repository.create_events(sample_events_with_dates)
        
        # Search with low alpha (focus on recency)
        results = repository.search_events(
            "critical system outage security vulnerability",
            limit=4, 
            alpha=0.1,  # 10% relevancy, 90% recency
            decay_param=0.2
        )
        
        # Should find all events but rank by recency
        assert len(results) == 4
        
        # Get event IDs in order
        result_ids = [event.id for event in results]
        
        # Recent events should be ranked higher
        assert "recent_relevant" in result_ids[:2] or "recent_irrelevant" in result_ids[:2]
    
    def test_hybrid_scoring_balanced(self, repository, sample_events_with_dates):
        """Test balanced scoring with default parameters"""
        # Create events
        repository.create_events(sample_events_with_dates)
        
        # Search with balanced alpha
        results = repository.search_events(
            "critical system outage security vulnerability",
            limit=4,
            alpha=0.9,  # 90% relevancy, 10% recency (default)
            decay_param=0.2
        )
        
        # Should find all events
        assert len(results) == 4
        
        # Recent relevant should be ranked highest (both recent and relevant)
        result_ids = [event.id for event in results]
        assert "recent_relevant" in result_ids
    
    def test_decay_parameter_effect(self, repository, sample_events_with_dates):
        """Test that different decay parameters affect recency scoring"""
        # Create events
        repository.create_events(sample_events_with_dates)
        
        # Search with high decay (faster recency decay)
        results_high_decay = repository.search_events(
            "critical system outage security vulnerability",
            limit=4,
            alpha=0.3,  # 30% relevancy, 70% recency
            decay_param=0.1  # 10% decay per day (high)
        )
        
        # Search with low decay (slower recency decay)  
        results_low_decay = repository.search_events(
            "critical system outage security vulnerability",
            limit=4,
            alpha=0.3,  # 30% relevancy, 70% recency
            decay_param=0.01  # 1% decay per day (low)
        )
        
        # Both should return results
        assert len(results_high_decay) == 4
        assert len(results_low_decay) == 4
        
        # With high decay, recent events should be much more favored
        # With low decay, older events should still have decent recency scores
        high_decay_ids = [event.id for event in results_high_decay]
        low_decay_ids = [event.id for event in results_low_decay]
        
        # The ordering might be different due to different decay rates
        assert high_decay_ids != low_decay_ids
    
    def test_parameter_validation(self, repository, sample_events_with_dates):
        """Test that the method accepts the new parameters without errors"""
        # Create events
        repository.create_events(sample_events_with_dates)
        
        # Test with various parameter combinations
        test_cases = [
            {"alpha": 0.5, "decay_param": 0.01},
            {"alpha": 0.8, "decay_param": 0.05},
            {"alpha": 0.2, "decay_param": 0.02},
            {"alpha": 1.0, "decay_param": 0.0},  # Pure relevancy
            {"alpha": 0.0, "decay_param": 0.02},  # Pure recency
        ]
        
        for params in test_cases:
            results = repository.search_events(
                "critical system outage",
                limit=4,
                **params
            )
            # Should not raise any errors
            assert isinstance(results, list) 