from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import os

from src.api.routes import router
from src.repositories.news_event_repository import InMemoryNewsEventRepository, ChromaDBNewsEventRepository

# GLOBAL SETTINGS
PORT = 8000
HOST = "0.0.0.0"
DEBUG = False
STORAGE_TYPE = "memory"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global repository instance
repository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    global repository
    
    logger.info("Starting IT Newsfeed Platform...")
    
    # Startup: Initialize repository based on configuration
    storage_type = STORAGE_TYPE
    
    if storage_type == "chromadb":
        chroma_dir = os.getenv("CHROMA_DIR", "./data/chromadb")
        logger.info(f"Initializing ChromaDB repository at {chroma_dir}")
        repository = ChromaDBNewsEventRepository(persist_directory=chroma_dir)
    else:
        logger.info("Initializing in-memory repository")
        repository = InMemoryNewsEventRepository()
    
    # Make repository available to routes
    app.state.repository = repository
    
    logger.info(f"Repository initialized with {repository.count_events()} existing events")
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down IT Newsfeed Platform...")
    if repository:
        logger.info("Cleaning up repository...")
        # Repository cleanup is handled by the implementation


app = FastAPI(
    title="IT Newsfeed Platform",
    description="Real-time IT news aggregation and filtering system",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "IT Newsfeed Platform"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info"
    )