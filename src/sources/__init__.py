"""
News source framework implementing Strategy + Adapter patterns.

This module provides the core abstractions for fetching and transforming
news data from various sources in a unified way.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Any, Optional
import logging
from dataclasses import dataclass

from src.models.domain import NewsEvent

logger = logging.getLogger(__name__)


# Strategy Pattern: How to fetch data
# 
# Protocol is used here to define a structural interface for DataFetcher.
# This allows any class with an async 'fetch' method matching this signature
# to be treated as a DataFetcher, without requiring explicit inheritance.
# This is useful for type checking and flexibility in plugging in different
# fetcher implementations (e.g., for JSON APIs, RSS, etc.) in the strategy pattern.
class DataFetcher(Protocol): 
    """Protocol defining how to fetch data from a source"""
    
    async def fetch(self, url: str, **kwargs) -> Any:
        """Fetch raw data from the given URL"""
        ...


# Adapter Pattern: How to transform source-specific data
class SourceAdapter(ABC):
    """Abstract base class for transforming source-specific data to NewsEvents"""
    
    @abstractmethod
    def adapt(self, raw_data: Any) -> list[NewsEvent]:
        """Transform raw source data into a list of NewsEvents"""
        pass
    
    def get_source_name(self) -> str:
        """Get the human-readable name of this source"""
        return self.__class__.__name__.replace('Adapter', '')


@dataclass
class SourceConfig:
    """Configuration for a news source"""
    name: str
    enabled: bool = True
    poll_interval: int = 300  # seconds
    source_type: str = "json_api"
    adapter_class: str = "GenericAdapter"
    url: str = ""
    headers: Optional[dict[str, str]] = None
    adapter_config: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.adapter_config is None:
            self.adapter_config = {}


class UniversalNewsSource:
    """
    Orchestrator that combines a DataFetcher strategy with a SourceAdapter
    to create a unified news source.
    """
    
    def __init__(self, config: SourceConfig, fetcher: DataFetcher, adapter: SourceAdapter):
        self.config = config
        self.fetcher = fetcher
        self.adapter = adapter
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
    
    async def get_events(self) -> list[NewsEvent]:
        """Fetch and transform events from this source"""
        try:
            self.logger.debug(f"Fetching events from {self.config.name}")
            
            # Use strategy to fetch data
            raw_data = await self.fetcher.fetch(
                self.config.url,
                headers=self.config.headers
            )
            
            # Use adapter to transform data
            events = self.adapter.adapt(raw_data)
            
            self.logger.info(f"Retrieved {len(events)} events from {self.config.name}")
            return events
            
        except Exception as e:
            self.logger.error(f"Error fetching events from {self.config.name}: {e}")
            return []
    
    def is_enabled(self) -> bool:
        """Check if this source is enabled"""
        return self.config.enabled
    
    def get_poll_interval(self) -> int:
        """Get the polling interval for this source"""
        return self.config.poll_interval 