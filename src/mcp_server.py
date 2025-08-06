"""
Simple MCP server for the IT Newsfeed Platform.
Exposes only the /retrieve API endpoint for retrieving news events.
"""

import asyncio
import logging
import os
import sys
from fastmcp import FastMCP
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Configuration
NEWSFEED_API_BASE_URL = os.getenv("NEWSFEED_API_BASE_URL", "http://localhost:8000")


# Create the MCP server
server = FastMCP("newsfeed")


@server.tool(
    name="retrieve_news_events",
    description="Retrieve IT-relevant news events from the newsfeed platform.",
)
async def retrieve_news_events(
    limit: int = 100,
    days_back: int = 14,
    alpha: float = 0.7,
    decay_param: float = 0.02
) -> str:
    """
    Retrieve IT-relevant news events from the newsfeed platform.
    
    Returns filtered events relevant to IT managers using hybrid relevancy + recency scoring.
    
    Args:
        limit: Maximum number of results to return (default: 100)
        days_back: Only return events from the last N days (default: 14)
        alpha: Weight for relevancy vs recency (0.7 = 70% relevancy, 30% recency) (default: 0.7)
        decay_param: Exponential decay parameter for recency scoring (0.02 = 2% decay per day) (default: 0.02)
    
    Returns:
        Formatted summary of IT-relevant news events
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Build query parameters
            query_params = {
                "limit": limit,
                "days_back": days_back,
                "alpha": alpha,
                "decay_param": decay_param
            }
            
            # Make request to the newsfeed API
            url = f"{NEWSFEED_API_BASE_URL}/retrieve"
            logger.info(f"Making request to {url} with params: {query_params}")
            
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            
            events = response.json()
            
            # Format the response
            if not events:
                return "No news events found matching the criteria."
            
            # Create a formatted summary
            summary = f"Retrieved {len(events)} IT-relevant news events:\n\n"
            
            for i, event in enumerate(events[:10], 1):  # Show first 10 events
                summary += f"{i}. {event.get('title', 'No title')}\n"
                summary += f"   Source: {event.get('source', 'Unknown')}\n"
                summary += f"   Published: {event.get('published_at', 'Unknown')}\n"
                if event.get('body'):
                    body_preview = event['body'][:100] + "..." if len(event['body']) > 100 else event['body']
                    summary += f"   Preview: {body_preview}\n"
                summary += "\n"
            
            if len(events) > 10:
                summary += f"... and {len(events) - 10} more events.\n\n"
            
            summary += f"Query parameters: limit={limit}, days_back={days_back}, alpha={alpha}, decay_param={decay_param}"
            
            return summary
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return f"Error retrieving news events: {error_msg}"
        except Exception as e:
            error_msg = f"Error retrieving news events: {str(e)}"
            logger.error(error_msg)
            return f"Error retrieving news events: {error_msg}"


async def main():
    """Main entry point for the MCP server"""
    try:
        logger.info("Starting Newsfeed MCP Server...")
        logger.info(f"Connecting to newsfeed API at: {NEWSFEED_API_BASE_URL}")
        await server.run_stdio_async()
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server...")


if __name__ == "__main__":
    asyncio.run(main()) 