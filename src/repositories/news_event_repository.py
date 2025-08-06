from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timedelta
from src.models.domain import NewsEvent, NewsType

import logging
import math
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class NewsEventRepository(ABC):
    """Abstract base repository for news events"""
    
    @abstractmethod
    def create_events(self, events: list[NewsEvent]) -> None:
        """Store a batch of news events"""
        pass
    
    @abstractmethod
    def get_all_events(self) -> list[NewsEvent]:
        """Retrieve all stored events"""
        pass
    
    @abstractmethod
    def get_event_by_id(self, event_id: str) -> Optional[NewsEvent]:
        """Retrieve a single event by ID"""
        pass
    
    @abstractmethod
    def count_events(self) -> int:
        """Count total number of stored events"""
        pass
    
    @abstractmethod
    def delete_all_events(self) -> None:
        """Delete all events (useful for testing)"""
        pass


class InMemoryNewsEventRepository(NewsEventRepository):
    """In-memory implementation of news event repository"""
    
    def __init__(self):
        self._events: list[NewsEvent] = []
        self._events_by_id: dict[str, NewsEvent] = {}
    
    def create_events(self, events: list[NewsEvent]) -> None:
        """Store a batch of news events"""
        for event in events:
            # Avoid duplicates based on ID
            if event.id not in self._events_by_id:
                self._events.append(event)
                self._events_by_id[event.id] = event
                logger.debug(f"Stored event: {event.id}")
            else:
                logger.debug(f"Event {event.id} already exists, skipping")
        
        logger.info(f"Stored {len(events)} events, total: {len(self._events)}")
    
    def get_all_events(self) -> list[NewsEvent]:
        """Retrieve all stored events"""
        return self._events.copy()  # Return copy to prevent external modification
    
    def get_event_by_id(self, event_id: str) -> Optional[NewsEvent]:
        """Retrieve a single event by ID"""
        return self._events_by_id.get(event_id)
    
    def count_events(self) -> int:
        """Count total number of stored events"""
        return len(self._events)
    
    def delete_all_events(self) -> None:
        """Delete all events (useful for testing)"""
        self._events.clear()
        self._events_by_id.clear()
        logger.info("Deleted all events")


class ChromaDBNewsEventRepository(NewsEventRepository):
    """ChromaDB implementation of news event repository"""
    
    def __init__(self, persist_directory: str = "./data/chromadb"):
        """Initialize ChromaDB client and collection"""
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="news_events",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"ChromaDB initialized with {self.collection.count()} existing events")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def create_events(self, events: list[NewsEvent]) -> None:
        """Store a batch of news events in ChromaDB"""
        if not events:
            return
        
        try:
            # Prepare data for ChromaDB
            ids = [event.id for event in events]
            documents = [f"{event.title} {event.body}".strip() for event in events]
            metadatas = [
                {
                    "source": event.source,
                    "title": event.title,
                    "body": event.body,
                    "published_at": event.published_at.isoformat(),
                    "published_at_timestamp": int(event.published_at.timestamp()),
                    "status": event.status,
                    "impact_level": event.impact_level,
                    "news_type": event.news_type.value if event.news_type else None,
                    "url": event.url,
                    "short_url": event.short_url,
                    "affected_components": ", ".join(event.affected_components) if event.affected_components else None,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "updated_at": event.updated_at.isoformat() if event.updated_at else None,
                    "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
                    "started_at": event.started_at.isoformat() if event.started_at else None,
                }
                for event in events
            ]
            
            # Upsert to ChromaDB (handles duplicates automatically)
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(events)} events in ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to store events in ChromaDB: {e}")
            raise
    
    def get_all_events(self) -> list[NewsEvent]:
        """Retrieve all stored events from ChromaDB"""
        try:
            result = self.collection.get()
            
            events = []
            for i, event_id in enumerate(result["ids"]):
                metadata = result["metadatas"][i]
                
                event = NewsEvent(
                    id=event_id,
                    source=metadata["source"],
                    title=metadata["title"],
                    body=metadata.get("body", ""),
                    published_at=datetime.fromisoformat(metadata["published_at"]),
                    status=metadata.get("status"),
                    impact_level=metadata.get("impact_level"),
                    news_type=NewsType(metadata.get("news_type")) if metadata.get("news_type") else NewsType.UNKNOWN,
                    url=metadata.get("url"),
                    short_url=metadata.get("short_url"),
                    affected_components=metadata.get("affected_components").split(", ") if metadata.get("affected_components") else None,
                    created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else None,
                    updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                    resolved_at=datetime.fromisoformat(metadata["resolved_at"]) if metadata.get("resolved_at") else None,
                    started_at=datetime.fromisoformat(metadata["started_at"]) if metadata.get("started_at") else None,
                )
                events.append(event)
            
            logger.info(f"Retrieved {len(events)} events from ChromaDB")
            return events
            
        except Exception as e:
            logger.error(f"Failed to retrieve events from ChromaDB: {e}")
            raise
    
    def get_event_by_id(self, event_id: str) -> Optional[NewsEvent]:
        """Retrieve a single event by ID from ChromaDB"""
        try:
            result = self.collection.get(ids=[event_id])
            
            if not result["ids"]:
                return None
            
            metadata = result["metadatas"][0]
            return NewsEvent(
                id=event_id,
                source=metadata["source"],
                title=metadata["title"],
                body=metadata.get("body", ""),
                published_at=datetime.fromisoformat(metadata["published_at"]),
                status=metadata.get("status"),
                impact_level=metadata.get("impact_level"),
                news_type=NewsType(metadata.get("news_type")) if metadata.get("news_type") else NewsType.UNKNOWN,
                url=metadata.get("url"),
                short_url=metadata.get("short_url"),
                affected_components=metadata.get("affected_components").split(", ") if metadata.get("affected_components") else None,
                created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else None,
                updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                resolved_at=datetime.fromisoformat(metadata["resolved_at"]) if metadata.get("resolved_at") else None,
                started_at=datetime.fromisoformat(metadata["started_at"]) if metadata.get("started_at") else None,
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve event {event_id} from ChromaDB: {e}")
            return None
    
    def count_events(self) -> int:
        """Count total number of stored events in ChromaDB"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count events in ChromaDB: {e}")
            return 0
    
    def delete_all_events(self) -> None:
        """Delete all events from ChromaDB (useful for testing)"""
        try:
            # ChromaDB doesn't have a direct "clear all" method
            # So we get all IDs and delete them
            result = self.collection.get()
            if result["ids"]:
                self.collection.delete(ids=result["ids"])
            
            logger.info("Deleted all events from ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to delete all events from ChromaDB: {e}")
            raise
    
    def search_events(self, query: str, limit: int = 10, days_back: int = None, 
                     alpha: float = 0.9, decay_param: float = 0.2) -> list[NewsEvent]:
        """Semantic search for events with hybrid relevancy + recency scoring
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            days_back: Optional filter to only return events from the last N days
            alpha: Weight for relevancy vs recency (0.7 = 70% relevancy, 30% recency)
            decay_param: Exponential decay parameter for recency scoring (0.02 = 2% decay per day)
        """
        try:
            # Calculate timestamp filter if days_back is specified
            where_filter = None
            if days_back is not None:
                cutoff_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp())
                where_filter = {"published_at_timestamp": {"$gte": cutoff_timestamp}}
            
            # Get more results than needed to allow for re-ranking
            search_limit = min(limit * 3, 100)  # Get up to 3x the requested limit, max 100
            
            results = self.collection.query(
                query_texts=[query],
                n_results=search_limit,
                where=where_filter,
                include=["metadatas", "distances"]  # Include distances for scoring
            )
            
            if not results["ids"][0]:
                return []
            
            # Calculate hybrid scores
            scored_events = []
            current_time = datetime.now()
            
            for i, event_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]  # ChromaDB distance (lower = more similar)
                
                # Calculate relevancy score (1 - distance, so higher = more relevant)
                relevancy_score = 1.0 - distance
                
                # Calculate recency score using exponential decay
                published_at = datetime.fromisoformat(metadata["published_at"])
                # Convert to naive datetime for consistent comparison
                if published_at.tzinfo is not None:
                    published_at = published_at.replace(tzinfo=None)
                if current_time.tzinfo is not None:
                    current_time = current_time.replace(tzinfo=None)
                
                days_old = (current_time - published_at).days
                recency_score = math.exp(-decay_param * days_old)
                
                # Combine scores with weights
                combined_score = alpha * relevancy_score + (1 - alpha) * recency_score
                
                event = NewsEvent(
                    id=event_id,
                    source=metadata["source"],
                    title=metadata["title"],
                    body=metadata.get("body", ""),
                    published_at=published_at,
                    status=metadata.get("status"),
                    impact_level=metadata.get("impact_level"),
                    news_type=NewsType(metadata.get("news_type")) if metadata.get("news_type") else NewsType.UNKNOWN,
                    url=metadata.get("url"),
                    short_url=metadata.get("short_url"),
                    affected_components=metadata.get("affected_components").split(", ") if metadata.get("affected_components") else None,
                    created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else None,
                    updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                    resolved_at=datetime.fromisoformat(metadata["resolved_at"]) if metadata.get("resolved_at") else None,
                    started_at=datetime.fromisoformat(metadata["started_at"]) if metadata.get("started_at") else None,
                )
                
                scored_events.append((event, combined_score, relevancy_score, recency_score))
            
            # Sort by combined score (highest first) and take top results
            scored_events.sort(key=lambda x: x[1], reverse=True)
            events = [event for event, _, _, _ in scored_events[:limit]]
            
            filter_info = f" (filtered to last {days_back} days)" if days_back is not None else ""
            logger.info(f"Found {len(events)} events for query: '{query}'{filter_info} with hybrid scoring (α={alpha}, decay={decay_param})")
            return events
            
        except Exception as e:
            logger.error(f"Failed to search events in ChromaDB: {e}")
            return []