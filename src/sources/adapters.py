"""
Source adapters for transforming different source formats into NewsEvents.

This module implements various SourceAdapter classes for handling
different data formats from various news sources.
"""

import logging
from typing import Any
from datetime import datetime
import uuid
import asyncio

from src.sources import SourceAdapter
from src.models.domain import NewsEvent, NewsType
from src.sources.fetchers import HackerNewsFetcher

logger = logging.getLogger(__name__)

# TODO verify data format!
class GitHubSecurityAdvisoriesAdapter(SourceAdapter):
    """Adapter for GitHub Security Advisories API"""
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform GitHub Security Advisories data into NewsEvents"""
        events = []
        
        if not isinstance(raw_data, list):
            logger.warning(f"Invalid GitHub Security Advisories data format - expected list, got {type(raw_data)}")
            return events
        
        for i, advisory in enumerate(raw_data):
            try:
                # Ensure advisory is a dict
                if not isinstance(advisory, dict):
                    logger.warning(f"Advisory {i} is not a dict: {type(advisory)}")
                    continue
                
                # Extract vulnerability information
                vulnerabilities = advisory.get('vulnerabilities', [])
                vulnerability = vulnerabilities[0] if vulnerabilities else {}
                
                severity = advisory.get('severity', 'unknown')
                
                # Map GitHub severity to impact level
                impact_level = self._map_severity_to_impact(severity)
                
                # Create detailed body with vulnerability information
                body = self._create_advisory_body(advisory, vulnerability)
                
                # Extract affected packages
                affected_components = self._extract_affected_packages(advisory)
                
                # Use GitHub Security Advisory ID (ghsa_id) if available, otherwise generate UUID
                event_id = advisory.get('ghsa_id', str(uuid.uuid4()))
                
                event = NewsEvent(
                    id=event_id,
                    source="GitHub Security Advisories",
                    title=advisory.get('summary', 'Security Advisory'),
                    body=body,
                    published_at=self._parse_github_datetime(advisory.get('published_at')),
                    status=advisory.get('state', 'unknown'),
                    impact_level=impact_level,
                    news_type=NewsType.SECURITY_ADVISORY,
                    url=advisory.get('html_url'),
                    affected_components=affected_components,
                    created_at=self._parse_github_datetime(advisory.get('created_at')),
                    updated_at=self._parse_github_datetime(advisory.get('updated_at'))
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing GitHub Security Advisory {i}: {e}")
                continue
        
        return events
    
    def _map_severity_to_impact(self, severity: str) -> str:
        """Map GitHub severity levels to impact levels"""
        severity_mapping = {
            'critical': 'critical',
            'high': 'major',
            'medium': 'minor',
            'low': 'minor',
            'unknown': 'none'
        }
        return severity_mapping.get(severity.lower(), 'none')
    
    def _create_advisory_body(self, advisory: dict, vulnerability: dict) -> str:
        """Create detailed body content for the advisory"""
        body_parts = []
        
        # Add description
        if advisory.get('description'):
            body_parts.append(f"Description: {advisory['description']}")
        
        # Add severity information
        if advisory.get('severity'):
            body_parts.append(f"Severity: {advisory['severity'].upper()}")
        
        # Add CVSS score if available
        cvss = advisory.get('cvss', {})
        if cvss and cvss.get('score'):
            body_parts.append(f"CVSS Score: {cvss['score']}")
        
        # Add affected packages
        vulnerabilities = advisory.get('vulnerabilities', [])
        if vulnerabilities:
            package_info = []
            for vuln in vulnerabilities:
                package = vuln.get('package', {})
                package_name = package.get('name', 'Unknown')
                ecosystem = package.get('ecosystem', 'Unknown')
                package_info.append(f"- {package_name} ({ecosystem})")
            
            if package_info:
                body_parts.append("Affected Packages:")
                body_parts.extend(package_info)
        
        # Add references
        references = advisory.get('references', [])
        if references:
            body_parts.append("References:")
            for ref in references:
                body_parts.append(f"- {ref}")
        
        return "\n".join(body_parts)
    
    def _extract_affected_packages(self, advisory: dict) -> list[str]:
        """Extract list of affected package names"""
        packages = []
        vulnerabilities = advisory.get('vulnerabilities', [])
        
        for vuln in vulnerabilities:
            package = vuln.get('package', {})
            package_name = package.get('name')
            ecosystem = package.get('ecosystem')
            
            if package_name and ecosystem:
                packages.append(f"{package_name} ({ecosystem})")
            elif package_name:
                packages.append(package_name)
        
        return packages
    
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
                # Create enriched body with incident updates
                body = self._create_incident_body(incident)
                
                # Extract affected components
                affected_components = self._extract_affected_components(incident)
                
                # Use source ID if available, otherwise generate UUID
                event_id = incident.get('id', str(uuid.uuid4())) # TODO deduplicate if using generated uuid
                
                event = NewsEvent(
                    id=event_id,
                    source="GitHub Status",
                    title=incident.get('name', 'GitHub Incident'),
                    body=body,
                    published_at=self._parse_github_datetime(incident.get('created_at')),
                    status=incident.get('status'),
                    impact_level=incident.get('impact'),
                    news_type=NewsType.SERVICE_STATUS,
                    url=incident.get('shortlink'),
                    short_url=incident.get('shortlink'),
                    affected_components=affected_components,
                    incident_updates=incident.get('incident_updates'),
                    created_at=self._parse_github_datetime(incident.get('created_at')),
                    updated_at=self._parse_github_datetime(incident.get('updated_at')),
                    resolved_at=self._parse_github_datetime(incident.get('resolved_at')),
                    started_at=self._parse_github_datetime(incident.get('started_at'))
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing GitHub incident: {e}")
                continue
        
        return events
    
    def _create_incident_body(self, incident: dict) -> str:
        """Create clean, searchable body content with incident updates"""
        body_parts = []
        
        # Add original body if available
        if incident.get('body'):
            body_parts.append(incident['body'])
        
        # Add incident updates in clean format
        updates = incident.get('incident_updates', [])
        if updates:
            # Sort updates by created_at timestamp (most recent first)
            sorted_updates = sorted(updates, key=lambda x: x.get('created_at', ''), reverse=True)
            
            for update in sorted_updates:
                created_at = update.get('created_at', '')
                status = update.get('status', 'Update')
                body_text = update.get('body', 'No details provided')
                
                # Format: "2025-08-05T16:08:53.475Z | investigating | Webhooks is experiencing degraded performance"
                if created_at:
                    # Parse and format timestamp for readability
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M UTC')
                    except:
                        formatted_time = created_at
                else:
                    formatted_time = "Unknown time"
                
                body_parts.append(f"{formatted_time} | {status} | {body_text}")
        
        return "\n".join(body_parts)
    
    def _extract_affected_components(self, incident: dict) -> list[str]:
        """Extract list of affected component names"""
        components = incident.get('components', [])
        return [comp.get('name', 'Unknown Component') for comp in components if comp.get('name')]
    
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





class HackerNewsAdapter(SourceAdapter):
    """Adapter for HackerNews API"""
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.fetcher = HackerNewsFetcher()
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Sync fallback - creates basic events without fetching details"""
        events = []
        
        if not isinstance(raw_data, list):
            logger.warning("Invalid HackerNews data format")
            return events
        
        # Create basic events with story IDs (fallback behavior)
        for story_id in raw_data[:self.max_items]:
            try:
                event_id = f"hn_{story_id}"
                event = NewsEvent(
                    id=event_id,
                    source="HackerNews",
                    title=f"HackerNews Top Story #{story_id}",
                    body=f"Story ID: {story_id} - Details not available in sync mode\n\n---\nSource: HackerNews",
                    published_at=datetime.now(),
                    url=f"https://news.ycombinator.com/item?id={story_id}",
                    news_type=NewsType.UNKNOWN
                )
                events.append(event)
            except Exception as e:
                logger.error(f"Error creating fallback HackerNews event: {e}")
                continue
        
        return events
    
    async def adapt_async(self, raw_data: Any) -> list[NewsEvent]:
        """Transform HackerNews data into NewsEvents with full story details"""
        events = []
        
        if not isinstance(raw_data, list):
            logger.warning("Invalid HackerNews data format")
            return events
        
        # Get story IDs from the top stories list
        story_ids = raw_data[:self.max_items]
        
        try:
            # Fetch actual story details for each story ID
            story_details = await self.fetcher.fetch_story_details(story_ids)
            
            for story in story_details:
                try:
                    # Skip if story is None or doesn't have required fields
                    if not story or 'id' not in story:
                        continue
                    
                    # Extract story information
                    story_id = story.get('id')
                    title = story.get('title', f'HackerNews Story #{story_id}')
                    url = story.get('url', f'https://news.ycombinator.com/item?id={story_id}')
                    score = story.get('score', 0)
                    descendants = story.get('descendants', 0)  # number of comments
                    author = story.get('by', 'Unknown')
                    time = story.get('time')
                    
                    # Create body with story details
                    body_parts = []
                    
                    # Prioritize actual story content
                    if story.get('text'):
                        # If it's a text post (Ask HN, Show HN, etc.), use the text as main content
                        body_parts.append(story.get('text'))
                    elif story.get('url'):
                        # For link posts, we could potentially fetch the page content
                        # For now, use the title as the main content since we have the URL
                        body_parts.append(f"Article: {title}")
                    
                    # Add metadata at the end
                    metadata_parts = []
                    metadata_parts.append(f"Posted by {author}")
                    if score > 0:
                        metadata_parts.append(f"Score: {score} points")
                    if descendants > 0:
                        metadata_parts.append(f"Comments: {descendants}")
                    
                    # Combine main content with metadata
                    if body_parts:
                        main_content = " ".join(body_parts)
                        metadata = " | ".join(metadata_parts)
                        body = f"{main_content}\n\n---\n{metadata}"
                    else:
                        body = " | ".join(metadata_parts)
                    
                    # Parse timestamp
                    published_at = datetime.fromtimestamp(time) if time else datetime.now()
                    
                    # Use HackerNews story ID as the unique identifier
                    event_id = f"hn_{story_id}"
                    
                    event = NewsEvent(
                        id=event_id,
                        source="HackerNews",
                        title=title,
                        body=body,
                        published_at=published_at,
                        url=url,
                        news_type=NewsType.UNKNOWN
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error processing HackerNews story {story.get('id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching HackerNews story details: {e}")
            # Fallback to creating basic events with story IDs
            for story_id in story_ids:
                try:
                    event_id = f"hn_{story_id}"
                    event = NewsEvent(
                        id=event_id,
                        source="HackerNews",
                        title=f"HackerNews Top Story #{story_id}",
                        body=f"Story ID: {story_id} - Unable to fetch details\n\n---\nSource: HackerNews",
                        published_at=datetime.now(),
                        url=f"https://news.ycombinator.com/item?id={story_id}",
                        news_type=NewsType.UNKNOWN
                    )
                    events.append(event)
                except Exception as e:
                    logger.error(f"Error creating fallback HackerNews event: {e}")
                    continue
        
        return events
    
    async def close(self):
        """Close the fetcher session"""
        await self.fetcher.close()


# TODO add Generic StatusPagee.io Adapter!
class GenericStatusAdapter(SourceAdapter):
    """Generic adapter for status pages following common patterns from StatusPage.io API"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
    
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform generic status page data into NewsEvents"""
        events = []
        
        # Extract configuration
        incidents_path = self.config.get('incidents_path', 'incidents')
        id_field = self.config.get('id_field', 'id')
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
                original_body = incident.get(body_field, '')
                date_str = incident.get(date_field)
                
                # Use source ID if available, otherwise generate UUID
                event_id = incident.get(id_field, str(uuid.uuid4()))
                
                # Create enriched body with incident updates
                body = self._create_incident_body(incident, original_body)
                
                # Extract additional fields
                affected_components = self._extract_affected_components(incident)
                
                event = NewsEvent(
                    id=event_id,
                    source=source_name,
                    title=title,
                    body=body,
                    published_at=self._parse_datetime(date_str),
                    status=incident.get('status'),
                    impact_level=incident.get('impact'),
                    news_type=NewsType.SERVICE_STATUS,
                    url=incident.get('shortlink'),
                    short_url=incident.get('shortlink'),
                    affected_components=affected_components,
                    incident_updates=incident.get('incident_updates'),
                    created_at=self._parse_datetime(incident.get('created_at')),
                    updated_at=self._parse_datetime(incident.get('updated_at')),
                    resolved_at=self._parse_datetime(incident.get('resolved_at')),
                    started_at=self._parse_datetime(incident.get('started_at'))
                )
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing incident: {e}")
                continue
        
        return events
    
    def _create_incident_body(self, incident: dict, original_body: str) -> str:
        """Create clean, searchable body content with incident updates"""
        body_parts = []
        
        # Add original body if available
        if original_body:
            body_parts.append(original_body)
        
        # Add incident updates in clean format
        updates = incident.get('incident_updates', [])
        if updates:
            # Sort updates by created_at timestamp (most recent first)
            sorted_updates = sorted(updates, key=lambda x: x.get('created_at', ''), reverse=True)
            
            for update in sorted_updates:
                created_at = update.get('created_at', '')
                status = update.get('status', 'Update')
                body_text = update.get('body', 'No details provided')
                
                # Format: "2025-08-05T16:08:53.475Z | investigating | Webhooks is experiencing degraded performance"
                if created_at:
                    # Parse and format timestamp for readability
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M UTC')
                    except:
                        formatted_time = created_at
                else:
                    formatted_time = "Unknown time"
                
                body_parts.append(f"{formatted_time} | {status} | {body_text}")
        
        return "\n".join(body_parts)
    
    def _extract_affected_components(self, incident: dict) -> list[str]:
        """Extract list of affected component names"""
        components = incident.get('components', [])
        return [comp.get('name', 'Unknown Component') for comp in components if comp.get('name')]
    
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
                url = item.get('link') or item.get('url')
                
                # Use URL as unique identifier for RSS items
                event_id = url if url else str(uuid.uuid4())
                
                event = NewsEvent(
                    id=event_id,
                    source=self.source_name,
                    title=title,
                    body=body,
                    published_at=self._parse_rss_datetime(date_str),
                    url=url,
                    news_type=NewsType.UNKNOWN
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
        
        # Try ISO format # TODO verify this!
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse RSS datetime: {date_str}")
            return datetime.now()