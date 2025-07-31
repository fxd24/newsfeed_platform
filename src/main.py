from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from src.api.routes import router

# GLOBAL SETTINGS
PORT = 8000
HOST = "0.0.0.0"
DEBUG = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    logger.info("Starting IT Newsfeed Platform...")
    
    # Startup: Initialize any needed resources
    # TODO
    # - Initialize ChromaDB connection
    # - Set up background task queues
    # - Validate configuration
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down IT Newsfeed Platform...")


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