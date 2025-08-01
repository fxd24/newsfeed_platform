"""
Services layer for business logic.

This module contains the core business logic services that coordinate
between the API layer and the data layer.
"""

from .ingestion_service import IngestionService

__all__ = ['IngestionService'] 