"""
Source adapters for transforming different source formats into NewsEvents.

This module implements various SourceAdapter classes for handling
different data formats from various news sources.
"""

import logging
from typing import Any
from datetime import datetime
import uuid

from src.sources import SourceAdapter
from src.models.domain import NewsEvent

logger = logging.getLogger(__name__)


class GitHubStatusAdapter(SourceAdapter):
    """Adapter for GitHub Status Page API"""
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform GitHub status data into NewsEvents"""
        events = []
        
        if not isinstance(raw_data, dict) or 'incidents' not in raw_data:
            logger.warning("Invalid GitHub status data format")
            return events
        
        for incident in raw_data['incidents']:
            try:
                # GitHub status incidents have a specific structure
                event = NewsEvent(
                    id=str(uuid.uuid4()),
                    source="GitHub Status",
                    title=incident.get('name', 'GitHub Incident'),
                    body=incident.get('body', ''),
                    published_at=self._parse_github_datetime(incident.get('created_at'))
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing GitHub incident: {e}")
                continue
        
        return events
    
    def _parse_github_datetime(self, date_str: str) -> datetime:
        """Parse GitHub's datetime format"""
        if not date_str:
            return datetime.now()
        
        try:
            # GitHub uses ISO 8601 format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse GitHub datetime: {date_str}")
            return datetime.now()


class AWSStatusAdapter(SourceAdapter):
    """Adapter for AWS Status Page API"""
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform AWS status data into NewsEvents"""
        events = []
        
        if not isinstance(raw_data, dict) or 'events' not in raw_data:
            logger.warning("Invalid AWS status data format")
            return events
        
        for event_data in raw_data['events']:
            try:
                event = NewsEvent(
                    id=str(uuid.uuid4()),
                    source="AWS Status",
                    title=event_data.get('summary', 'AWS Event'),
                    body=event_data.get('description', ''),
                    published_at=self._parse_aws_datetime(event_data.get('start_time'))
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing AWS event: {e}")
                continue
        
        return events
    
    def _parse_aws_datetime(self, date_str: str) -> datetime:
        """Parse AWS datetime format"""
        if not date_str:
            return datetime.now()
        
        try:
            # AWS uses ISO 8601 format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse AWS datetime: {date_str}")
            return datetime.now()


class HackerNewsAdapter(SourceAdapter):
    """Adapter for HackerNews API"""
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform HackerNews data into NewsEvents"""
        events = []
        
        if not isinstance(raw_data, list):
            logger.warning("Invalid HackerNews data format")
            return events
        
        # HackerNews API returns list of story IDs
        # We'd need to fetch individual stories, but for now we'll create mock events
        for i, story_id in enumerate(raw_data[:self.max_items]):
            try:
                event = NewsEvent(
                    id=str(uuid.uuid4()),
                    source="HackerNews",
                    title=f"HackerNews Story #{story_id}",
                    body=f"Top story from HackerNews with ID {story_id}",
                    published_at=datetime.now()
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing HackerNews story: {e}")
                continue
        
        return events


class GenericStatusAdapter(SourceAdapter):
    """Generic adapter for status pages following common patterns"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform generic status page data into NewsEvents"""
        events = []
        
        # Extract configuration
        incidents_path = self.config.get('incidents_path', 'incidents')
        title_field = self.config.get('title_field', 'title')
        body_field = self.config.get('body_field', 'body')
        date_field = self.config.get('date_field', 'created_at')
        source_name = self.config.get('source_name', 'Status Page')
        
        # Navigate to incidents array
        data = raw_data
        for path_part in incidents_path.split('.'):
            if isinstance(data, dict) and path_part in data:
                data = data[path_part]
            else:
                logger.warning(f"Could not find path {incidents_path} in data")
                return events
        
        if not isinstance(data, list):
            logger.warning(f"Expected list at {incidents_path}, got {type(data)}")
            return events
        
        for incident in data:
            try:
                # Extract fields with fallbacks
                title = incident.get(title_field, f'{source_name} Incident')
                body = incident.get(body_field, '')
                date_str = incident.get(date_field)
                
                event = NewsEvent(
                    id=str(uuid.uuid4()),
                    source=source_name,
                    title=title,
                    body=body,
                    published_at=self._parse_datetime(date_str)
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing incident: {e}")
                continue
        
        return events
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse datetime with multiple format support"""
        if not date_str:
            return datetime.now()
        
        # Try common datetime formats
        formats = [
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse datetime: {date_str}")
            return datetime.now()


class RSSAdapter(SourceAdapter):
    """Adapter for RSS/Atom feeds"""
    
    def __init__(self, source_name: str = "RSS Feed"):
        self.source_name = source_name
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform RSS/Atom feed data into NewsEvents"""
        events = []
        
        if not isinstance(raw_data, dict) or 'items' not in raw_data:
            logger.warning("Invalid RSS data format")
            return events
        
        for item in raw_data['items']:
            try:
                # Handle both RSS and Atom formats
                title = item.get('title', 'RSS Item')
                body = item.get('description') or item.get('content', '')
                date_str = item.get('pubDate') or item.get('published')
                
                event = NewsEvent(
                    id=str(uuid.uuid4()),
                    source=self.source_name,
                    title=title,
                    body=body,
                    published_at=self._parse_rss_datetime(date_str)
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing RSS item: {e}")
                continue
        
        return events
    
    def _parse_rss_datetime(self, date_str: str) -> datetime:
        """Parse RSS datetime formats"""
        if not date_str:
            return datetime.now()
        
        # Common RSS datetime formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 822 with timezone name
            '%Y-%m-%dT%H:%M:%SZ',        # ISO 8601
            '%Y-%m-%dT%H:%M:%S.%fZ'      # ISO 8601 with microseconds
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse RSS datetime: {date_str}")
            return datetime.now() 