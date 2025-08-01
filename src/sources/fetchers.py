"""
Data fetcher strategies for different transport protocols.

This module implements various DataFetcher strategies for fetching
data from different types of sources (JSON APIs, RSS feeds, etc.).
"""

import aiohttp
import logging
from typing import Any, Optional
import xml.etree.ElementTree as ET
import json


logger = logging.getLogger(__name__)


class JSONAPIFetcher:
    """Fetcher for JSON API endpoints"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session
    
    async def fetch(self, url: str, **kwargs) -> Any:
        """Fetch JSON data from the given URL"""
        session = await self._get_session()
        
        headers = kwargs.get('headers', {})
        headers.setdefault('User-Agent', 'Newsfeed-Platform/1.0')
        
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class RSSFetcher:
    """Fetcher for RSS/Atom feeds"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session
    
    async def fetch(self, url: str, **kwargs) -> Any:
        """Fetch RSS/Atom data from the given URL"""
        session = await self._get_session()
        
        headers = kwargs.get('headers', {})
        headers.setdefault('User-Agent', 'Newsfeed-Platform/1.0')
        
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                content = await response.text()
                
                # Parse XML
                root = ET.fromstring(content)
                return self._parse_feed(root)
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching RSS {url}: {e}")
            raise
        except ET.ParseError as e:
            logger.error(f"XML parse error for {url}: {e}")
            raise
    
    def _parse_feed(self, root: ET.Element) -> dict[str, Any]:
        """Parse RSS/Atom feed into a structured format"""
        # Handle both RSS and Atom feeds
        if root.tag.endswith('rss'):
            return self._parse_rss(root)
        elif root.tag.endswith('feed'):
            return self._parse_atom(root)
        else:
            raise ValueError(f"Unknown feed format: {root.tag}")
    
    def _parse_rss(self, root: ET.Element) -> dict[str, Any]:
        """Parse RSS feed"""
        channel = root.find('channel')
        if channel is None:
            raise ValueError("No channel element found in RSS feed")
        
        items = []
        for item in channel.findall('item'):
            items.append({
                'title': self._get_text(item, 'title'),
                'description': self._get_text(item, 'description'),
                'link': self._get_text(item, 'link'),
                'pubDate': self._get_text(item, 'pubDate'),
                'guid': self._get_text(item, 'guid')
            })
        
        return {
            'title': self._get_text(channel, 'title'),
            'description': self._get_text(channel, 'description'),
            'items': items
        }
    
    def _parse_atom(self, root: ET.Element) -> dict[str, Any]:
        """Parse Atom feed"""
        items = []
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            items.append({
                'title': self._get_text(entry, '{http://www.w3.org/2005/Atom}title'),
                'content': self._get_text(entry, '{http://www.w3.org/2005/Atom}content'),
                'link': self._get_link(entry),
                'published': self._get_text(entry, '{http://www.w3.org/2005/Atom}published'),
                'id': self._get_text(entry, '{http://www.w3.org/2005/Atom}id')
            })
        
        return {
            'title': self._get_text(root, '{http://www.w3.org/2005/Atom}title'),
            'items': items
        }
    
    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Safely get text from an XML element"""
        child = element.find(tag)
        return child.text if child is not None else ""
    
    def _get_link(self, element: ET.Element) -> str:
        """Get link from Atom entry"""
        link_elem = element.find('{http://www.w3.org/2005/Atom}link')
        if link_elem is not None:
            return link_elem.get('href', '')
        return ""
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class MockFetcher:
    """Mock fetcher for testing purposes"""
    
    def __init__(self, mock_data: Any):
        self.mock_data = mock_data
    
    async def fetch(self, url: str, **kwargs) -> Any:
        """Return mock data"""
        logger.debug(f"Mock fetcher returning data for {url}")
        return self.mock_data 