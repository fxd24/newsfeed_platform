from pydantic import BaseModel
from datetime import datetime


class NewsEvent(BaseModel):
    """Base news event model matching the API contract"""
    id: str
    source: str
    title: str
    body: str = ""
    published_at: datetime
    
    class Config:
        # Allow datetime parsing from ISO strings
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }