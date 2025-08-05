from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class NewsType(str, Enum):
    """Enumeration of news types"""
    SERVICE_STATUS = "service_status"
    SECURITY_ADVISORY = "security_advisory"
    SOFTWARE_BUG = "software_bug"
    UNKNOWN = "unknown"

# TODO other news event types: possible. decide how to handle them. like just as other.
# MAINTENANCE: For scheduled maintenance events
# ANNOUNCEMENT: For general announcements
# PERFORMANCE: For performance-related issues


class NewsEvent(BaseModel):
    """Base news event model matching the API contract with extended fields"""
    model_config = ConfigDict()
    
    # Core API contract fields
    id: str
    source: str
    title: str
    body: str = ""
    published_at: datetime
    
    # Extended fields for enhanced functionality
    status: Optional[str] = None  # Current status (unknown/identified/investigating/monitoring/resolved)
    impact_level: Optional[str] = None  # Impact level (unknown/critical/major/minor/none)
    news_type: Optional[NewsType] = NewsType.UNKNOWN  # Type of news item
    url: Optional[str] = None  # Link to the incident/article
    short_url: Optional[str] = None  # Short link
    
    # Rich content fields
    affected_components: Optional[List[str]] = None  # List of affected services
    incident_updates: Optional[List[Dict]] = None  # Detailed updates
    created_at: Optional[datetime] = None  # Creation timestamp
    updated_at: Optional[datetime] = None  # Last update timestamp
    resolved_at: Optional[datetime] = None  # Resolution timestamp
    started_at: Optional[datetime] = None  # Start timestamp
    
    @field_serializer('published_at')
    def serialize_published_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
    
    @field_serializer('resolved_at')
    def serialize_resolved_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
    
    @field_serializer('started_at')
    def serialize_started_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None