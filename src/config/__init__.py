"""
Configuration management for the newsfeed platform.

This module handles loading and managing configuration for sources,
scheduling, and other platform settings.
"""

from .config_manager import ConfigManager, load_config_from_file, load_config_from_dict

__all__ = ['ConfigManager', 'load_config_from_file', 'load_config_from_dict'] 