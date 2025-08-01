"""
Configuration manager for loading and managing source configurations.
"""

import yaml
import json
import logging
from typing import Any, Optional
from pathlib import Path

from src.sources import SourceConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manager for loading and validating source configurations"""
    
    def __init__(self):
        self.sources: dict[str, SourceConfig] = {}
        self.global_config: dict[str, Any] = {}
    
    def load_from_file(self, file_path: str) -> bool:
        """Load configuration from a YAML or JSON file"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Configuration file not found: {file_path}")
                return False
            
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    logger.error(f"Unsupported configuration file format: {path.suffix}")
                    return False
            
            return self.load_from_dict(config_data)
            
        except Exception as e:
            logger.error(f"Error loading configuration from {file_path}: {e}")
            return False
    
    def load_from_dict(self, config_data: dict[str, Any]) -> bool:
        """Load configuration from a dictionary"""
        try:
            # Load global configuration
            self.global_config = config_data.get('global', {})
            
            # Load source configurations
            sources_data = config_data.get('sources', {})
            self.sources.clear()
            
            for source_name, source_data in sources_data.items():
                try:
                    config = self._create_source_config(source_name, source_data)
                    self.sources[source_name] = config
                    logger.info(f"Loaded source configuration: {source_name}")
                    
                except Exception as e:
                    logger.error(f"Error loading source {source_name}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.sources)} source configurations")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def _create_source_config(self, name: str, data: dict[str, Any]) -> SourceConfig:
        """Create a SourceConfig from dictionary data"""
        return SourceConfig(
            name=name,
            enabled=data.get('enabled', True),
            poll_interval=data.get('poll_interval', 300),
            source_type=data.get('source_type', 'json_api'),
            adapter_class=data.get('adapter_class', 'GenericAdapter'),
            url=data.get('url', ''),
            headers=data.get('headers'),
            adapter_config=data.get('adapter_config')
        )
    
    def get_source_configs(self) -> list[SourceConfig]:
        """Get all source configurations"""
        return list(self.sources.values())
    
    def get_enabled_source_configs(self) -> list[SourceConfig]:
        """Get enabled source configurations"""
        return [config for config in self.sources.values() if config.enabled]
    
    def get_source_config(self, name: str) -> Optional[SourceConfig]:
        """Get a specific source configuration"""
        return self.sources.get(name)
    
    def add_source_config(self, config: SourceConfig) -> bool:
        """Add a source configuration"""
        try:
            self.sources[config.name] = config
            logger.info(f"Added source configuration: {config.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding source configuration {config.name}: {e}")
            return False
    
    def remove_source_config(self, name: str) -> bool:
        """Remove a source configuration"""
        if name in self.sources:
            del self.sources[name]
            logger.info(f"Removed source configuration: {name}")
            return True
        return False
    
    def get_global_config(self) -> dict[str, Any]:
        """Get global configuration"""
        return self.global_config.copy()
    
    def validate_configs(self) -> list[str]:
        """Validate all source configurations and return error messages"""
        errors = []
        
        for name, config in self.sources.items():
            if not config.url:
                errors.append(f"Source {name}: Missing URL")
            
            if config.poll_interval < 60:
                errors.append(f"Source {name}: Poll interval too short ({config.poll_interval}s)")
            
            if not config.adapter_class:
                errors.append(f"Source {name}: Missing adapter class")
        
        return errors


def load_config_from_file(file_path: str) -> ConfigManager:
    """Convenience function to load configuration from file"""
    manager = ConfigManager()
    if not manager.load_from_file(file_path):
        raise ValueError(f"Failed to load configuration from {file_path}")
    return manager


def load_config_from_dict(config_data: dict[str, Any]) -> ConfigManager:
    """Convenience function to load configuration from dictionary"""
    manager = ConfigManager()
    if not manager.load_from_dict(config_data):
        raise ValueError("Failed to load configuration from dictionary")
    return manager 