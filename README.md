# IT Newsfeed Platform

A real-time IT news aggregation and filtering system with configurable sources, built with FastAPI and ChromaDB.

## 🚀 Quick Start

### Prerequisites

1. **Install uv** (Python package manager from Astral):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install make** (if not already installed):
   - **macOS**: `brew install make`
   - **Ubuntu/Debian**: `sudo apt-get install make`


### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd newsfeed_platform
   ```

2. **Install dependencies**:
   ```bash
   make sync
   ```

3. **Configure sources**:
   Edit `config/sources.yaml` and set `enabled: true` for the sources you want to use:
   ```yaml
   sources:
     github_status:
       enabled: true  # Change from false to true
       poll_interval: 300
       # ... rest of config
     
     hackernews:
       enabled: true  # Change from false to true
       poll_interval: 600
       # ... rest of config
   ```

4. **Start the development server**:
   ```bash
   make dev
   ```
   This starts the FastAPI server with API endpoints and database on `http://localhost:8000`

5. **Start the Streamlit UI** (in a new terminal):
   ```bash
   make ui
   ```
   This opens the web interface on `http://localhost:8501`

## 🎯 Available Commands

- `make dev` - Start the development server (API + database)
- `make ui` - Start the Streamlit web interface
- `make tests` - Run the test suite
- `make lint` - Check code quality with ruff
- `make fix` - Auto-fix linting issues
- `make sync` - Sync dependencies with uv

## 🔧 Configuration

### Source Configuration

Edit `config/sources.yaml` to enable and configure news sources:

```yaml
sources:
  github_status:
    enabled: true  # Set to true to enable this source
    poll_interval: 300  # Poll every 5 minutes
    source_type: "json_api"
    adapter_class: "GitHubStatusAdapter"
    url: "https://www.githubstatus.com/api/v2/incidents.json"
    
  hackernews:
    enabled: true  # Set to true to enable this source
    poll_interval: 600  # Poll every 10 minutes
    source_type: "hackernews"
    adapter_class: "HackerNewsAdapter"
    url: "https://hacker-news.firebaseio.com/v0/topstories.json"
    adapter_config:
      max_items: 10
```

### Polling Intervals

You can adjust how frequently sources are polled:
- `poll_interval: 300` = 5 minutes
- `poll_interval: 600` = 10 minutes  
- `poll_interval: 900` = 15 minutes
- `poll_interval: 1800` = 30 minutes

## 🔌 API Usage Examples

### Ingest Events

```bash
# Ingest events from an external source
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual_ingest",
    "title": "Critical Security Update",
    "body": "Important security patch released for production systems",
    "published_at": "2024-01-15T10:30:00Z"
  }'
```

### Retrieve Events

```bash
# Get latest events with default scoring (70% relevancy, 30% recency)
curl "http://localhost:8000/retrieve?limit=20"

# Get events from last 7 days with custom scoring
curl "http://localhost:8000/retrieve?limit=50&days_back=7&alpha=0.8&decay_param=0.01"

# Get all stored events without filtering
curl "http://localhost:8000/retrieve/all"
```

### Manual Polling

If you don't want to wait for the scheduled polling, you can manually trigger it:

```bash
# Poll all enabled sources immediately
curl -X POST "http://localhost:8000/admin/poll/all"

# Poll a specific source
curl -X POST "http://localhost:8000/admin/poll/github_status"
```

### Check System Status

```bash
# Get overall system status
curl "http://localhost:8000/admin/status"

# Check source configurations
curl "http://localhost:8000/admin/sources"

# View scheduler status
curl "http://localhost:8000/admin/scheduler"

# Get ingestion statistics
curl "http://localhost:8000/admin/stats"
```

## 🤖 MCP Server Setup

The platform includes a Model Context Protocol (MCP) server for AI tool integration.

### Prerequisites

1. **Ensure the main server is running**:
   ```bash
   make dev
   ```

2. **Make the MCP script executable**:
   ```bash
   chmod +x mcp_server.sh
   ```

3. **Start the MCP server**:
   ```bash
   ./mcp_server.sh
   ```

### MCP Client Configuration

Configure your MCP client (e.g., Claude Desktop App, Cursor IDE) with:

```json
{
  "mcpServers": {
    "newsfeed": {
      "command": "/absolute/path/to/newsfeed_platform/mcp_server.sh",
      "cwd": "/absolute/path/to/newsfeed_platform"
    }
  }
}
```

**Important**: Replace `/absolute/path/to/newsfeed_platform/` with the actual path to your project directory.

### MCP Usage

Once configured, you can ask your AI tool questions like:
- "What are the latest IT news events?"
- "Show me critical security incidents from the last week"
- "Get the top 20 most relevant IT events"

## 🧪 Testing

Run the complete test suite:

```bash
make tests
```

Run tests with coverage:

```bash
uv run pytest tests/ --cov=src
```

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

### Admin Endpoints

- `GET /admin/status` - Detailed system status
- `GET /admin/sources` - Source status and configuration
- `GET /admin/scheduler` - Scheduler status and jobs
- `GET /admin/stats` - Ingestion statistics
- `POST /admin/poll/all` - Manually poll all sources
- `POST /admin/poll/{source_name}` - Manually poll specific source

## 🚀 Features

- **Configurable Sources**: Add new sources via YAML configuration
- **Multiple Data Formats**: JSON APIs, RSS feeds, custom adapters
- **Background Polling**: Automatic data collection with APScheduler
- **Unified Ingestion**: Same service handles polling and external API calls
- **Admin Interface**: Monitor and control sources via REST API
- **Production Ready**: Error handling, logging, health checks
- **Hybrid Scoring**: Advanced relevancy + recency scoring system
- **MCP Integration**: AI tool integration via Model Context Protocol

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
- **AI Integration**: MCP server for AI tool integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `make tests`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.