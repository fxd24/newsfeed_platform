from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime


class NewsEvent(BaseModel):
    """Base news event model matching the API contract"""
    model_config = ConfigDict()
    
    id: str
    source: str
    title: str
    body: str = ""
    published_at: datetime
    
    @field_serializer('published_at')
    def serialize_published_at(self, value: datetime) -> str:
        return value.isoformat()