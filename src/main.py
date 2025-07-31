from typing import Any
from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IT Newsfeed Platform", version="1.0.0")

# In-memory storage
events_storage: list[dict[str, Any]] = []

@app.post("/ingest")
def ingest_events(events: list[dict[str, Any]]):
    """Accept JSON array and store it"""
    events_storage.extend(events)
    return {"status": "ok"}

@app.get("/retrieve")
def retrieve_events():
    """Return all stored events"""
    return events_storage

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)