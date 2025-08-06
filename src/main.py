from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import logging
import os
from typing import Optional

from src.api.routes import router
from src.repositories.news_event_repository import InMemoryNewsEventRepository, ChromaDBNewsEventRepository
from src.sources.factory import SourceManager
from src.services import IngestionService
from src.scheduler import SchedulerManager
from src.config import ConfigManager

# GLOBAL SETTINGS
PORT = 8000
HOST = "0.0.0.0"
DEBUG = False
STORAGE_TYPE = "chromadb"  # chromadb | inmemory
CONFIG_FILE = os.getenv("CONFIG_FILE", "config/sources.yaml")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/newsfeed_platform.log')
    ]
)
logger = logging.getLogger(__name__)

# Global instances
repository: Optional[InMemoryNewsEventRepository | ChromaDBNewsEventRepository] = None
source_manager: Optional[SourceManager] = None
ingestion_service: Optional[IngestionService] = None
scheduler_manager: Optional[SchedulerManager] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    global repository, source_manager, ingestion_service, scheduler_manager, config_manager
    
    logger.info("Starting IT Newsfeed Platform...")
    
    # Startup: Initialize components
    try:
        # 1. Initialize repository
        storage_type = STORAGE_TYPE
        
        if storage_type == "chromadb":
            chroma_dir = os.getenv("CHROMA_DIR", "./data/chromadb")
            logger.info(f"Initializing ChromaDB repository at {chroma_dir}")
            repository = ChromaDBNewsEventRepository(persist_directory=chroma_dir)
        else:
            logger.info("Initializing in-memory repository")
            repository = InMemoryNewsEventRepository()
        
        # 2. Initialize services
        ingestion_service = IngestionService(repository)
        source_manager = SourceManager()
        
        # 3. Load configuration
        config_manager = ConfigManager()
        if os.path.exists(CONFIG_FILE):
            logger.info(f"Loading configuration from {CONFIG_FILE}")
            if not config_manager.load_from_file(CONFIG_FILE):
                logger.warning("Failed to load configuration file, using defaults")
                # Load default configuration
                default_config = {
                    'sources': {
                        'github_status': {
                            'enabled': True,
                            'poll_interval': 300,
                            'source_type': 'json_api',
                            'adapter_class': 'GitHubStatusAdapter',
                            'url': 'https://www.githubstatus.com/api/v2/incidents.json'
                        },
                        'hackernews': {
                            'enabled': True,
                            'poll_interval': 600,
                            'source_type': 'json_api',
                            'adapter_class': 'HackerNewsAdapter',
                            'url': 'https://hacker-news.firebaseio.com/v0/topstories.json',
                            'adapter_config': {
                                'max_items': 10
                            }
                        }
                    }
                }
                config_manager.load_from_dict(default_config)
        else:
            logger.warning(f"Configuration file {CONFIG_FILE} not found, using defaults")
            # Load default configuration
            default_config = {
                'sources': {
                    'github_status': {
                        'enabled': True,
                        'poll_interval': 300,
                        'source_type': 'json_api',
                        'adapter_class': 'GitHubStatusAdapter',
                        'url': 'https://www.githubstatus.com/api/v2/incidents.json'
                    }
                }
            }
            config_manager.load_from_dict(default_config)
        
        # 4. Initialize sources from configuration
        for config in config_manager.get_enabled_source_configs():
            if source_manager.add_source(config):
                logger.info(f"Added source: {config.name}")
            else:
                logger.error(f"Failed to add source: {config.name}")
        
        # 5. Initialize scheduler
        scheduler_manager = SchedulerManager(source_manager, ingestion_service)
        scheduler_manager.start()
        
        # 6. Add polling jobs
        job_count = scheduler_manager.add_all_source_jobs()
        logger.info(f"Added {job_count} polling jobs")
        
        # Make components available to routes
        app.state.repository = repository
        app.state.source_manager = source_manager
        app.state.ingestion_service = ingestion_service
        app.state.scheduler_manager = scheduler_manager
        app.state.config_manager = config_manager
        
        logger.info(f"Repository initialized with {repository.count_events()} existing events")
        logger.info("IT Newsfeed Platform started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down IT Newsfeed Platform...")
    
    try:
        if scheduler_manager:
            scheduler_manager.shutdown()
            logger.info("Scheduler shutdown complete")
        
        if repository:
            logger.info("Repository cleanup complete")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="IT Newsfeed Platform",
    description="Real-time IT news aggregation and filtering system with configurable sources",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global scheduler_manager, source_manager
    
    status = {
        "status": "healthy",
        "service": "IT Newsfeed Platform",
        "scheduler_running": scheduler_manager.is_running() if scheduler_manager else False,
        "active_jobs": scheduler_manager.get_job_count() if scheduler_manager else 0,
        "enabled_sources": len(source_manager.get_enabled_sources()) if source_manager else 0
    }
    
    return status


@app.get("/admin/status")
async def admin_status(request: Request):
    """Admin status endpoint with detailed information"""
    scheduler_manager = getattr(request.app.state, 'scheduler_manager', None)
    source_manager = getattr(request.app.state, 'source_manager', None)
    config_manager = getattr(request.app.state, 'config_manager', None)
    
    if not all([scheduler_manager, source_manager, config_manager]):
        return {"error": "Components not initialized"}
    
    return {
        "scheduler": {
            "running": scheduler_manager.is_running(),
            "job_count": scheduler_manager.get_job_count(),
            "job_status": scheduler_manager.get_job_status()
        },
        "sources": {
            "total": len(source_manager.get_all_sources()),
            "enabled": len(source_manager.get_enabled_sources()),
            "status": source_manager.get_source_status()
        },
        "configuration": {
            "config_file": CONFIG_FILE,
            "config_loaded": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info"
    )