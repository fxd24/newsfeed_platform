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

## 🔌 API Endpoints

### Core Endpoints

- `POST /ingest` - Ingest events from external sources
- `GET /retrieve` - Retrieve all stored events
- `GET /health` - Health check

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