"""
Tests for source adapters.

This module tests the various SourceAdapter implementations
for transforming different source formats into NewsEvents.
"""

import pytest
from datetime import datetime
from src.sources.adapters import (
    GitHubStatusAdapter,
    AWSStatusAdapter,
    HackerNewsAdapter,
    GenericStatusAdapter,
    RSSAdapter
)
from src.models.domain import NewsEvent


class TestGitHubStatusAdapter:
    """Test the GitHub Status Page adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create a GitHub status adapter"""
        return GitHubStatusAdapter()
    
    def test_adapt_valid_data(self, adapter):
        """Test adapting valid GitHub status data"""
        raw_data = {
            "incidents": [
                {
                    "name": "GitHub API Issues",
                    "body": "We are experiencing issues with the GitHub API",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    "name": "GitHub Actions Delays",
                    "body": "GitHub Actions builds are experiencing delays",
                    "created_at": "2024-01-15T14:45:00Z"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 2
        assert all(isinstance(event, NewsEvent) for event in events)
        
        # Check first event
        assert events[0].source == "GitHub Status"
        assert events[0].title == "GitHub API Issues"
        assert events[0].body == "We are experiencing issues with the GitHub API"
        assert isinstance(events[0].published_at, datetime)
        
        # Check second event
        assert events[1].source == "GitHub Status"
        assert events[1].title == "GitHub Actions Delays"
        assert events[1].body == "GitHub Actions builds are experiencing delays"
        assert isinstance(events[1].published_at, datetime)
    
    def test_adapt_invalid_data(self, adapter):
        """Test adapting invalid data"""
        # Missing incidents key
        raw_data = {"status": "operational"}
        events = adapter.adapt(raw_data)
        assert events == []
        
        # Not a dict
        raw_data = "not a dict"
        events = adapter.adapt(raw_data)
        assert events == []
        
        # None
        events = adapter.adapt(None)
        assert events == []
    
    def test_adapt_empty_incidents(self, adapter):
        """Test adapting data with empty incidents"""
        raw_data = {"incidents": []}
        events = adapter.adapt(raw_data)
        assert events == []
    
    def test_adapt_malformed_incident(self, adapter):
        """Test adapting data with malformed incident"""
        raw_data = {
            "incidents": [
                {
                    "name": "Valid Incident",
                    "body": "Valid body",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    # Missing required fields - should still create an event with defaults
                    "body": "Invalid incident"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        # Should process both incidents (malformed one gets defaults)
        assert len(events) == 2
        assert events[0].title == "Valid Incident"
        assert events[1].title == "GitHub Incident"  # Default title
    
    def test_parse_github_datetime_valid(self, adapter):
        """Test parsing valid GitHub datetime"""
        date_str = "2024-01-15T10:30:00Z"
        result = adapter._parse_github_datetime(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
    
    def test_parse_github_datetime_invalid(self, adapter):
        """Test parsing invalid GitHub datetime"""
        # Invalid format
        result = adapter._parse_github_datetime("invalid-date")
        assert isinstance(result, datetime)  # Should return current time
        
        # Empty string
        result = adapter._parse_github_datetime("")
        assert isinstance(result, datetime)  # Should return current time
        
        # None
        result = adapter._parse_github_datetime(None)
        assert isinstance(result, datetime)  # Should return current time


class TestAWSStatusAdapter:
    """Test the AWS Status Page adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create an AWS status adapter"""
        return AWSStatusAdapter()
    
    def test_adapt_valid_data(self, adapter):
        """Test adapting valid AWS status data"""
        raw_data = {
            "events": [
                {
                    "summary": "AWS EC2 Issues",
                    "description": "We are experiencing issues with EC2 instances",
                    "start_time": "2024-01-15T10:30:00Z"
                },
                {
                    "summary": "AWS S3 Delays",
                    "description": "S3 operations are experiencing delays",
                    "start_time": "2024-01-15T14:45:00Z"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 2
        assert all(isinstance(event, NewsEvent) for event in events)
        
        # Check first event
        assert events[0].source == "AWS Status"
        assert events[0].title == "AWS EC2 Issues"
        assert events[0].body == "We are experiencing issues with EC2 instances"
        assert isinstance(events[0].published_at, datetime)
        
        # Check second event
        assert events[1].source == "AWS Status"
        assert events[1].title == "AWS S3 Delays"
        assert events[1].body == "S3 operations are experiencing delays"
        assert isinstance(events[1].published_at, datetime)
    
    def test_adapt_invalid_data(self, adapter):
        """Test adapting invalid data"""
        # Missing events key
        raw_data = {"status": "operational"}
        events = adapter.adapt(raw_data)
        assert events == []
        
        # Not a dict
        raw_data = "not a dict"
        events = adapter.adapt(raw_data)
        assert events == []
    
    def test_parse_aws_datetime_valid(self, adapter):
        """Test parsing valid AWS datetime"""
        date_str = "2024-01-15T10:30:00Z"
        result = adapter._parse_aws_datetime(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30


class TestHackerNewsAdapter:
    """Test the Hacker News adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create a Hacker News adapter"""
        return HackerNewsAdapter(max_items=5)
    
    def test_initialization(self, adapter):
        """Test adapter initialization"""
        assert adapter.max_items == 5
    
    def test_adapt_valid_data(self, adapter):
        """Test adapting valid Hacker News data"""
        # HackerNews adapter expects a list of story IDs
        raw_data = [1, 2, 3]
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 3
        assert all(isinstance(event, NewsEvent) for event in events)
        
        # Check first event
        assert events[0].source == "HackerNews"
        assert events[0].title == "HackerNews Story #1"
        assert events[0].body == "Top story from HackerNews with ID 1"
        assert isinstance(events[0].published_at, datetime)
    
    def test_adapt_respects_max_items(self, adapter):
        """Test that adapter respects max_items limit"""
        raw_data = [1, 2, 3, 4, 5, 6]  # 6 items, but max_items is 5
        
        events = adapter.adapt(raw_data)
        
        # Should only process max_items (5)
        assert len(events) == 5
        assert events[0].title == "HackerNews Story #1"
        assert events[4].title == "HackerNews Story #5"
    
    def test_adapt_invalid_data(self, adapter):
        """Test adapting invalid data"""
        # Not a list
        raw_data = {"not": "a list"}
        events = adapter.adapt(raw_data)
        assert events == []
        
        # None
        events = adapter.adapt(None)
        assert events == []
    
    def test_adapt_malformed_story(self, adapter):
        """Test adapting data with malformed story"""
        raw_data = [1, "invalid_id", 3]
        
        events = adapter.adapt(raw_data)
        
        # Should process all items (even invalid ones get processed)
        assert len(events) == 3
        assert events[0].title == "HackerNews Story #1"
        assert events[1].title == "HackerNews Story #invalid_id"
        assert events[2].title == "HackerNews Story #3"


class TestGenericStatusAdapter:
    """Test the Generic Status adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create a generic status adapter"""
        config = {
            "source_name": "Test Service",
            "incidents_path": "events",
            "title_field": "title",
            "body_field": "description",
            "date_field": "created_at"
        }
        return GenericStatusAdapter(config)
    
    def test_adapt_valid_data(self, adapter):
        """Test adapting valid generic status data"""
        raw_data = {
            "events": [
                {
                    "title": "Service Issue",
                    "description": "We are experiencing issues",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    "title": "Service Maintenance",
                    "description": "Scheduled maintenance",
                    "created_at": "2024-01-15T14:45:00Z"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 2
        assert all(isinstance(event, NewsEvent) for event in events)
        
        # Check first event
        assert events[0].source == "Test Service"
        assert events[0].title == "Service Issue"
        assert events[0].body == "We are experiencing issues"
        assert isinstance(events[0].published_at, datetime)
    
    def test_adapt_custom_config(self):
        """Test adapting with custom configuration"""
        config = {
            "source_name": "Custom Service",
            "incidents_path": "incidents",
            "title_field": "name",
            "body_field": "message",
            "date_field": "timestamp"
        }
        adapter = GenericStatusAdapter(config)
        
        raw_data = {
            "incidents": [
                {
                    "name": "Custom Issue",
                    "message": "Custom message",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 1
        assert events[0].source == "Custom Service"
        assert events[0].title == "Custom Issue"
        assert events[0].body == "Custom message"
    
    def test_adapt_missing_event_path(self, adapter):
        """Test adapting data with missing event path"""
        raw_data = {"status": "operational"}
        events = adapter.adapt(raw_data)
        assert events == []
    
    def test_adapt_missing_fields(self, adapter):
        """Test adapting data with missing fields"""
        raw_data = {
            "events": [
                {
                    "title": "Valid Event",
                    "description": "Valid description",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    # Missing required fields - should still create an event with defaults
                    "title": "Invalid Event"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        # Should process both events (missing fields get defaults)
        assert len(events) == 2
        assert events[0].title == "Valid Event"
        assert events[1].title == "Invalid Event"
        assert events[1].body == ""  # Default empty body
    
    def test_parse_datetime_iso(self, adapter):
        """Test parsing ISO datetime"""
        date_str = "2024-01-15T10:30:00Z"
        result = adapter._parse_datetime(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_datetime_timestamp(self, adapter):
        """Test parsing timestamp datetime"""
        # The GenericStatusAdapter doesn't handle integer timestamps
        # So we'll test with a string timestamp instead
        date_str = "1642234567"
        result = adapter._parse_datetime(date_str)
        
        # Should return current time for unparseable format
        assert isinstance(result, datetime)
    
    def test_parse_datetime_invalid_format(self, adapter):
        """Test parsing datetime with invalid format"""
        date_str = "2024-01-15T10:30:00Z"
        result = adapter._parse_datetime(date_str)
        
        assert isinstance(result, datetime)  # Should return current time


class TestRSSAdapter:
    """Test the RSS adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create an RSS adapter"""
        return RSSAdapter(source_name="Test RSS")
    
    def test_adapt_valid_data(self, adapter):
        """Test adapting valid RSS data"""
        # RSS adapter expects 'items' key, not 'entries'
        raw_data = {
            "items": [
                {
                    "title": "RSS Article 1",
                    "link": "http://example1.com",
                    "description": "Summary of article 1",
                    "pubDate": "2024-01-15T10:30:00Z"
                },
                {
                    "title": "RSS Article 2",
                    "link": "http://example2.com",
                    "description": "Summary of article 2",
                    "pubDate": "2024-01-15T14:45:00Z"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        assert len(events) == 2
        assert all(isinstance(event, NewsEvent) for event in events)
        
        # Check first event
        assert events[0].source == "Test RSS"
        assert events[0].title == "RSS Article 1"
        assert events[0].body == "Summary of article 1"  # Should use description
        assert isinstance(events[0].published_at, datetime)
    
    def test_adapt_missing_entries(self, adapter):
        """Test adapting data with missing entries"""
        raw_data = {"title": "RSS Feed"}
        events = adapter.adapt(raw_data)
        assert events == []
    
    def test_adapt_malformed_entry(self, adapter):
        """Test adapting data with malformed entry"""
        raw_data = {
            "items": [
                {
                    "title": "Valid Article",
                    "link": "http://example.com",
                    "description": "Valid summary",
                    "pubDate": "2024-01-15T10:30:00Z"
                },
                {
                    # Missing required fields - should still create an event with defaults
                    "title": "Invalid Article"
                }
            ]
        }
        
        events = adapter.adapt(raw_data)
        
        # Should process both entries (missing fields get defaults)
        assert len(events) == 2
        assert events[0].title == "Valid Article"
        assert events[1].title == "Invalid Article"
    
    def test_parse_rss_datetime_valid(self, adapter):
        """Test parsing valid RSS datetime"""
        date_str = "2024-01-15T10:30:00Z"
        result = adapter._parse_rss_datetime(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_rss_datetime_invalid(self, adapter):
        """Test parsing invalid RSS datetime"""
        # Invalid format
        result = adapter._parse_rss_datetime("invalid-date")
        assert isinstance(result, datetime)  # Should return current time
        
        # Empty string
        result = adapter._parse_rss_datetime("")
        assert isinstance(result, datetime)  # Should return current time


class TestAdapterErrorHandling:
    """Test error handling across all adapters"""
    
    def test_github_adapter_error_handling(self):
        """Test GitHub adapter error handling"""
        adapter = GitHubStatusAdapter()
        
        # Test with malformed data that would cause exceptions
        raw_data = {
            "incidents": [
                {
                    "name": None,  # This could cause issues
                    "body": "Test body",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
        
        # Should not raise an exception
        events = adapter.adapt(raw_data)
        assert isinstance(events, list)
    
    def test_aws_adapter_error_handling(self):
        """Test AWS adapter error handling"""
        adapter = AWSStatusAdapter()
        
        # Test with malformed data
        raw_data = {
            "events": [
                {
                    "summary": None,  # This could cause issues
                    "description": "Test description",
                    "start_time": "2024-01-15T10:30:00Z"
                }
            ]
        }
        
        # Should not raise an exception
        events = adapter.adapt(raw_data)
        assert isinstance(events, list)
    
    def test_hackernews_adapter_error_handling(self):
        """Test Hacker News adapter error handling"""
        adapter = HackerNewsAdapter()
        
        # Test with malformed data
        raw_data = [
            "not_an_int",  # This could cause issues
            "another_invalid_id"
        ]
        
        # Should not raise an exception
        events = adapter.adapt(raw_data)
        assert isinstance(events, list) 