# IT Newsfeed Platform

A real-time IT news aggregation and filtering system with configurable sources, built with FastAPI and ChromaDB.

## 🏗️ Architecture

The platform uses a **Strategy + Adapter pattern** for maximum flexibility:

- **Strategy Pattern**: Different data fetchers (JSON API, RSS, etc.)
- **Adapter Pattern**: Source-specific data transformers
- **Factory Pattern**: Easy source creation from configuration
- **APScheduler**: Background polling with configurable intervals

### Core Components

```
┌─────────────────────────────────────────┐
│ APScheduler + FastAPI Routes            │  ← Orchestration
├─────────────────────────────────────────┤
│ SourceManager + IngestionService        │  ← Business Logic  
├─────────────────────────────────────────┤
│ UniversalNewsSource                     │  ← Coordination
├─────────────────────────────────────────┤
│ DataFetcher (Strategy) | SourceAdapter  │  ← Transport + Transform
├─────────────────────────────────────────┤
│ ChromaDB Repository                     │  ← Persistence
└─────────────────────────────────────────┘
```

## 🚀 Features

- **Configurable Sources**: Add new sources via YAML configuration
- **Multiple Data Formats**: JSON APIs, RSS feeds, custom adapters
- **Background Polling**: Automatic data collection with APScheduler
- **Unified Ingestion**: Same service handles polling and external API calls
- **Admin Interface**: Monitor and control sources via REST API
- **Production Ready**: Error handling, logging, health checks

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd newsfeed_platform
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Run the application**:
   ```bash
   python -m src.main
   ```

The server will start on `http://localhost:8000`

4. **Optional: Set up MCP server** (for AI tool integration):
   ```bash
   chmod +x mcp_server.sh
   ./mcp_server.sh
   ```

## ⚙️ Configuration

Sources are configured via `config/sources.yaml`:

```yaml
sources:
  github_status:
    enabled: true
    poll_interval: 300  # 5 minutes
    source_type: "json_api"
    adapter_class: "GitHubStatusAdapter"
    url: "https://www.githubstatus.com/api/v2/incidents.json"
    
  hackernews:
    enabled: true
    poll_interval: 600  # 10 minutes
    source_type: "json_api"
    adapter_class: "HackerNewsAdapter"
    url: "https://hacker-news.firebaseio.com/v0/topstories.json"
    adapter_config:
      max_items: 10
```

### Source Types

- **JSON APIs**: `json_api` - Standard REST APIs
- **RSS Feeds**: `rss` - RSS/Atom feeds
- **Mock**: `mock` - For testing

### Adapter Classes

- **GitHubStatusAdapter**: GitHub Status Page
- **AWSStatusAdapter**: AWS Status Page
- **HackerNewsAdapter**: HackerNews API
- **GenericStatusAdapter**: Configurable for any status page
- **RSSAdapter**: RSS/Atom feeds

## 🎯 Hybrid Relevancy + Recency Scoring

The platform uses an advanced hybrid scoring system that combines semantic relevancy with exponential decay recency to provide optimal search results for IT managers.

### Scoring Formula

```
Combined Score = α × relevancy_score + (1-α) × recency_score
```

Where:
- **relevancy_score** = 1 - ChromaDB distance (higher = more relevant)
- **recency_score** = exp(-decay_param × days_old)
- **α (alpha)** = Weight for relevancy vs recency (default: 0.7)
- **decay_param** = Exponential decay rate (default: 0.02 = 2% decay per day)

### Parameter Examples

- **α=0.9**: 90% relevancy, 10% recency (focus on content relevance)
- **α=0.7**: 70% relevancy, 30% recency (balanced approach - DEFAULT)
- **α=0.1**: 10% relevancy, 90% recency (focus on recent events)
- **decay=0.02**: 2% decay per day (DEFAULT)
- **decay=0.1**: 10% decay per day (faster decay)
- **decay=0.01**: 1% decay per day (slower decay)

### Example API Usage

```bash
# Default balanced scoring
GET /retrieve

# Relevancy-focused search
GET /retrieve?alpha=0.9&decay_param=0.02

# Recency-focused search
GET /retrieve?alpha=0.1&decay_param=0.02

# High decay rate (events age quickly)
GET /retrieve?alpha=0.5&decay_param=0.1

# Low decay rate (events stay relevant longer)
GET /retrieve?alpha=0.5&decay_param=0.01
```

## 🔌 API Endpoints

### Core Endpoints

- `POST /ingest` - Ingest events from external sources
- `GET /retrieve` - Retrieve events with hybrid relevancy + recency scoring
  - Query parameters:
    - `limit` (int, default: 100): Maximum number of results
    - `days_back` (int, default: 14): Only return events from last N days
    - `alpha` (float, default: 0.7): Relevancy weight (0.0-1.0)
    - `decay_param` (float, default: 0.02): Recency decay parameter
- `GET /retrieve/all` - Retrieve all stored events without filtering
- `GET /health` - Health check

## 🤖 MCP Server

The platform includes a Model Context Protocol (MCP) server that allows AI tools (like Cursor IDE, Claude Desktop App, etc.) to retrieve IT-relevant news events directly.

### Features

- **Single Tool**: Only exposes the `/retrieve` API endpoint
- **IT-Focused**: Returns events relevant to IT managers using hybrid relevancy + recency scoring
- **Configurable Parameters**: Supports all parameters from the original API
- **Simple Integration**: Easy to integrate with any MCP-compatible AI tool

### Available Tool

#### `retrieve_news_events`

Retrieves IT-relevant news events from the newsfeed platform.

**Parameters:**
- `limit` (integer, default: 100): Maximum number of results to return
- `days_back` (integer, default: 14): Only return events from the last N days
- `alpha` (number, default: 0.7): Weight for relevancy vs recency (0.7 = 70% relevancy, 30% recency)
- `decay_param` (number, default: 0.02): Exponential decay parameter for recency scoring

**Returns:** Formatted summary of IT-relevant news events with titles, sources, and previews.

### Setup

1. **Make the script executable**:
   ```bash
   chmod +x mcp_server.sh
   ```

2. **Start the MCP server**:
   ```bash
   ./mcp_server.sh
   ```

### Configuration for MCP Clients

Use the following configuration in your MCP client (e.g., Claude Desktop App, Cursor IDE):

```json
{
  "mcpServers": {
    "newsfeed": {
      "command": "/path/to/your/newsfeed_platform/mcp_server.sh",
      "cwd": "/path/to/your/newsfeed_platform"
    }
  }
}
```

**Important**: Replace `/path/to/your/newsfeed_platform/` with the actual absolute path to your newsfeed platform directory.

### Environment Variables

- `NEWSFEED_API_BASE_URL`: Override the default API URL (default: `http://localhost:8000`)

### Usage Example

When integrated with an MCP client, you can ask questions like:

- "What are the latest IT news events?"
- "Show me critical security incidents from the last week"
- "Get the top 20 most relevant IT events"

The MCP server will automatically call the `/retrieve` API with appropriate parameters and return a formatted summary of the events.

### Admin Endpoints

- `GET /admin/status` - Detailed system status
- `GET /admin/sources` - Source status and configuration
- `GET /admin/scheduler` - Scheduler status and jobs
- `GET /admin/stats` - Ingestion statistics
- `POST /admin/poll/all` - Manually poll all sources
- `POST /admin/poll/{source_name}` - Manually poll specific source

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=src
```

## 🔧 Adding New Sources

### 1. Create an Adapter (if needed)

```python
from src.sources import SourceAdapter
from src.models.domain import NewsEvent

class MyServiceAdapter(SourceAdapter):
    def adapt(self, raw_data: Any) -> List[NewsEvent]:
        events = []
        for item in raw_data['items']:
            event = NewsEvent(
                id=str(uuid.uuid4()),
                source="My Service",
                title=item['title'],
                body=item['description'],
                published_at=datetime.fromisoformat(item['date'])
            )
            events.append(event)
        return events
```

### 2. Register the Adapter

```python
from src.sources.factory import SourceFactory

factory = SourceFactory()
factory.register_adapter('MyServiceAdapter', MyServiceAdapter)
```

### 3. Add Configuration

```yaml
sources:
  my_service:
    enabled: true
    poll_interval: 300
    source_type: "json_api"
    adapter_class: "MyServiceAdapter"
    url: "https://api.myservice.com/status"
```

## 🏭 Production Deployment

### Environment Variables

- `CONFIG_FILE`: Path to configuration file (default: `config/sources.yaml`)
- `STORAGE_TYPE`: `memory` or `chromadb` (default: `memory`)
- `CHROMA_DIR`: ChromaDB persistence directory (default: `./data/chromadb`)

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8000

CMD ["python", "-m", "src.main"]
```

## 📊 Monitoring

The platform provides comprehensive monitoring:

- **Health Checks**: `/health` endpoint
- **Source Status**: `/admin/sources` shows enabled/disabled sources
- **Scheduler Status**: `/admin/scheduler` shows polling job status
- **Ingestion Stats**: `/admin/stats` shows event counts and rates

## 🔄 Background Polling

The platform automatically polls configured sources:

- **GitHub Status**: Every 5 minutes
- **HackerNews**: Every 10 minutes
- **RSS Feeds**: Every 15 minutes
- **Custom intervals**: Configurable per source

## 🎯 Key Benefits

- **Minimal Code**: New sources require only configuration
- **High Reusability**: Same fetchers work across multiple sources
- **Easy Extension**: Add sources without code changes
- **Production Ready**: Error handling, retries, monitoring
- **Type Safe**: Full type hints throughout
- **Testable**: Each component tested in isolation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.