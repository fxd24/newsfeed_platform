"""
Source factory and manager for creating and managing news sources.

This module provides the factory pattern for creating UniversalNewsSource
instances and a manager for coordinating all sources.
"""

import logging
from typing import Type, Any

from src.sources import UniversalNewsSource, SourceConfig, SourceAdapter, DataFetcher
from src.sources.fetchers import JSONAPIFetcher, RSSFetcher, MockFetcher
from src.sources.adapters import (
    GitHubStatusAdapter, HackerNewsAdapter,
    GenericStatusAdapter, RSSAdapter, GitHubSecurityAdvisoriesAdapter
)

logger = logging.getLogger(__name__)


class SourceFactory:
    """Factory for creating UniversalNewsSource instances"""
    
    def __init__(self):
        self._fetcher_registry: dict[str, Type[DataFetcher]] = {
            'json_api': JSONAPIFetcher,
            'rss': RSSFetcher,
            'mock': MockFetcher
        }
        
        self._adapter_registry: dict[str, Type[SourceAdapter]] = {
            'GitHubStatusAdapter': GitHubStatusAdapter,
            'HackerNewsAdapter': HackerNewsAdapter,
            'GenericStatusAdapter': GenericStatusAdapter,
            'RSSAdapter': RSSAdapter,
            'GitHubSecurityAdvisoriesAdapter': GitHubSecurityAdvisoriesAdapter,
            'GenericAdapter': GenericStatusAdapter  # Alias for backward compatibility
        }
    
    def create_source(self, config: SourceConfig) -> UniversalNewsSource:
        """Create a UniversalNewsSource from configuration"""
        try:
            # Create fetcher
            fetcher_class = self._fetcher_registry.get(config.source_type)
            if not fetcher_class:
                raise ValueError(f"Unknown source type: {config.source_type}")
            
            # Handle special cases for fetcher initialization
            if config.source_type == 'mock':
                # MockFetcher requires mock_data
                fetcher = fetcher_class({})
            else:
                fetcher = fetcher_class()
            
            # Create adapter
            adapter_class = self._adapter_registry.get(config.adapter_class)
            if not adapter_class:
                raise ValueError(f"Unknown adapter class: {config.adapter_class}")
            
            # Handle adapter-specific initialization
            if config.adapter_class in ['GenericStatusAdapter', 'GenericAdapter']:
                adapter = adapter_class(config.adapter_config or {})
            elif config.adapter_class == 'RSSAdapter':
                source_name = config.adapter_config.get('source_name', config.name) if config.adapter_config else config.name
                adapter = adapter_class(source_name)
            elif config.adapter_class == 'HackerNewsAdapter':
                max_items = config.adapter_config.get('max_items', 10) if config.adapter_config else 10
                adapter = adapter_class(max_items)
            else:
                adapter = adapter_class()
            
            return UniversalNewsSource(config, fetcher, adapter)
            
        except Exception as e:
            logger.error(f"Error creating source {config.name}: {e}")
            raise
    
    def register_fetcher(self, name: str, fetcher_class: Type[DataFetcher]):
        """Register a custom fetcher class"""
        self._fetcher_registry[name] = fetcher_class
    
    def register_adapter(self, name: str, adapter_class: Type[SourceAdapter]):
        """Register a custom adapter class"""
        self._adapter_registry[name] = adapter_class


class SourceManager:
    """Manager for coordinating all news sources"""
    
    def __init__(self, factory: SourceFactory = None):
        self.factory = factory or SourceFactory()
        self.sources: dict[str, UniversalNewsSource] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_source(self, config: SourceConfig) -> bool:
        """Add a source to the manager"""
        try:
            if config.name in self.sources:
                self.logger.warning(f"Source {config.name} already exists, replacing")
            
            source = self.factory.create_source(config)
            self.sources[config.name] = source
            self.logger.info(f"Added source: {config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add source {config.name}: {e}")
            return False
    
    def remove_source(self, name: str) -> bool:
        """Remove a source from the manager"""
        if name in self.sources:
            del self.sources[name]
            self.logger.info(f"Removed source: {name}")
            return True
        return False
    
    def get_source(self, name: str) -> UniversalNewsSource:
        """Get a source by name"""
        return self.sources.get(name)
    
    def get_enabled_sources(self) -> list[UniversalNewsSource]:
        """Get all enabled sources"""
        return [source for source in self.sources.values() if source.is_enabled()]
    
    def get_all_sources(self) -> list[UniversalNewsSource]:
        """Get all sources (enabled and disabled)"""
        return list(self.sources.values())
    
    async def fetch_all_events(self) -> list[Any]:
        """Fetch events from all enabled sources"""
        all_events = []
        
        for source in self.get_enabled_sources():
            try:
                events = await source.get_events()
                all_events.extend(events)
                self.logger.debug(f"Fetched {len(events)} events from {source.config.name}")
                
            except Exception as e:
                self.logger.error(f"Error fetching from {source.config.name}: {e}")
                continue
        
        self.logger.info(f"Total events fetched: {len(all_events)}")
        return all_events
    
    async def fetch_source_events(self, source_name: str) -> list[Any]:
        """Fetch events from a specific source"""
        source = self.get_source(source_name)
        if not source:
            self.logger.warning(f"Source {source_name} not found")
            return []
        
        if not source.is_enabled():
            self.logger.warning(f"Source {source_name} is disabled")
            return []
        
        try:
            events = await source.get_events()
            self.logger.info(f"Fetched {len(events)} events from {source_name}")
            return events
            
        except Exception as e:
            self.logger.error(f"Error fetching from {source_name}: {e}")
            return []
        finally:
            # Ensure proper cleanup of HTTP sessions
            try:
                await source.fetcher.close()
            except Exception as cleanup_error:
                self.logger.warning(f"Error closing fetcher for {source_name}: {cleanup_error}")
    
    def get_source_status(self) -> dict[str, dict[str, Any]]:
        """Get status information for all sources"""
        status = {}
        
        for name, source in self.sources.items():
            status[name] = {
                'enabled': source.is_enabled(),
                'poll_interval': source.get_poll_interval(),
                'url': source.config.url,
                'adapter_class': source.config.adapter_class,
                'source_type': source.config.source_type
            }
        
        return status 