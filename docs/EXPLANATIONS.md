# IT Newsfeed Platform - Technical Documentation

## Project Overview

This project implements a **scalable, real-time newsfeed platform** that aggregates and filters IT-related events from multiple public sources, stores them in a searchable datastore, and ranks them by balancing importance and recency. The system is designed specifically for **IT managers** who need to stay informed about:

- Major service outages and incidents
- Critical cybersecurity threats and vulnerabilities  
- Infrastructure disruptions
- Critical software bugs and security patches

The platform provides both REST API endpoints for programmatic access and a web-based UI, making it integration-ready for future applications like chatbots and recommendation engines.

### Key Design Philosophy

The entire system is architected to run efficiently on **low-compute environments** while maintaining the flexibility to scale performance significantly with additional resources. This approach makes it accessible for smaller organizations while providing clear scaling paths for enterprise deployments.

## User Persona & Requirements Analysis

**Primary User**: IT Manager responsible for infrastructure monitoring and incident response

**Core Needs**:
- Real-time awareness of critical IT events affecting their infrastructure
- Prioritized information flow that balances relevance with recency
- Quick identification of actionable incidents vs. informational updates
- Integration capabilities with existing monitoring and alerting systems

**Time Sensitivity Assumptions**:
- Events from the last hour are most critical
- 24-hour window captures immediate operational concerns
- One-week retention covers trending issues and follow-up actions
- Events older than 14 days are generally not operationally relevant

## Architecture & Design Patterns

### Core Architectural Patterns

The system leverages multiple design patterns to achieve modularity, extensibility, and maintainability:

#### 1. **Strategy + Adapter Pattern Combination**
```
DataFetcher (Strategy) → Handles different data source types (JSON, RSS, etc.)
SourceAdapter (Adapter) → Transforms source-specific data to unified domain model
```

This dual-pattern approach separates **transport concerns** from **data transformation**, enabling:
- Easy addition of new data source types without code changes
- Source-specific customization while maintaining consistent internal data models
- Independent testing and evolution of fetching vs. transformation logic

#### 2. **Repository Pattern**
Provides clean abstraction over data persistence, allowing seamless switching between storage backends:
- **Development**: In-memory storage for rapid iteration
- **Production**: ChromaDB for vector search and metadata filtering
- **Future**: Cloud-based solutions with minimal code changes

#### 3. **Factory Pattern**
Dynamic source creation from YAML configuration eliminates hardcoded dependencies and enables runtime source management.

### System Architecture Overview

```
┌─────────────────────────────────────────┐
│ APScheduler + FastAPI Routes            │  ← Orchestration Layer
├─────────────────────────────────────────┤
│ SourceManager + IngestionService        │  ← Business Logic Layer
├─────────────────────────────────────────┤
│ UniversalNewsSource                     │  ← Coordination Layer
├─────────────────────────────────────────┤
│ DataFetcher (Strategy) | SourceAdapter  │  ← Transport + Transform
├─────────────────────────────────────────┤
│ ChromaDB Repository                     │  ← Persistence Layer
└─────────────────────────────────────────┘
```

## Data Aggregation and Ingestion

### Source Configuration System

The platform uses **YAML-based configuration** for maximum flexibility without code changes:

```yaml
sources:
  github_status:
    enabled: true
    poll_interval: 300  # 5 minutes
    source_type: "json_api"
    adapter_class: "GitHubStatusAdapter"
    url: "https://www.githubstatus.com/api/v2/incidents.json"
```

### Polling Strategy with APScheduler

**APScheduler** provides robust background polling with built-in benefits:
- **Retry logic**: Automatic handling of transient failures
- **Logging**: Built-in job execution tracking
- **Concurrency control**: Prevents overlapping polls
- **Dynamic scheduling**: Runtime job modification capabilities

### Current Limitations & Future Improvements

**Embedding Computation Bottleneck**: Currently, embeddings are computed synchronously during ingestion, which limits throughput.

**Future Scaling Strategy**:
1. **Dedicated processors per source**: Parallel processing pipelines
2. **Pre-computed embeddings**: Batch embedding generation
3. **Demand-based scaling**: Dynamic compute allocation based on ingestion load
4. **Async processing**: Decouple ingestion from embedding computation

**Event Classification Enhancement**: Many sources lack structured metadata (event type, impact level, status). A future enhancement would deploy a lightweight LLM classifier to:
- Categorize event types (outage, security, maintenance, etc.)
- Infer impact levels (critical, major, minor)
- Determine current status (ongoing, resolved, investigating)

This enrichment would significantly improve retrieval accuracy and ranking quality.

## Content Filtering and Hybrid Ranking System

### Filtering Mechanism

The system implements a **dual-filter approach**:

1. **Temporal Filter**: Removes events older than 14 days by default
2. **Semantic Filter**: Vector similarity scoring using sentence-transformers model `all-MiniLM-L6-v2`

**Model Selection Rationale**: The `all-MiniLM-L6-v2` model provides an optimal balance of:
- Speed: Fast inference suitable for real-time systems
- Accuracy: Sufficient semantic understanding for IT domain content
- Size: Manageable memory footprint for low-compute deployments

### Hybrid Scoring Formula

The system uses a sophisticated scoring mechanism that balances semantic relevance with temporal recency:

```
Combined Score = α × relevancy_score + (1-α) × recency_score

Where:
- relevancy_score = 1 - ChromaDB_cosine_distance
- recency_score = exp(-decay_param × days_since_published)
- α (alpha) = Relevancy weight [0.0-1.0] (default: 0.7)
- decay_param = Exponential decay rate (default: 0.02)
```

### Parameter Tuning Analysis

Through empirical analysis, the default parameters provide optimal balance:

**Decay Rate 0.02 Analysis**:
- Recent (1-6 hours): 94% score retention
- 24 hours: 62% score retention  
- 1 week: 3.5% score retention
- Provides natural 17.8x preference for daily vs. weekly events

**Alpha Values**:
- **α=0.9**: Heavy relevance focus (research scenarios)
- **α=0.7**: Balanced approach (default for IT managers)
- **α=0.3**: Recency-focused (breaking news scenarios)

### Current Limitations & Future Work

**Source-Specific Decay Rates**: Different event types have different relevance windows:
- **Status pages**: Fast decay (incidents resolve quickly)
- **Security advisories**: Slow decay (vulnerabilities remain relevant until patched)
- **Infrastructure announcements**: Medium decay (planned changes have extended timelines)

**Content Quality Filtering**: Current semantic similarity can over-rank generic security content that provides little actionable value. Future classification could filter out:
- Generic security awareness content
- Marketing announcements disguised as technical updates
- Duplicate reports of the same incident across sources

## Storage and Searchability

### Data Model Design

The system uses **Pydantic models** for robust data validation and type safety:

```python
class NewsEvent(BaseModel):
    id: str
    source: str
    title: str
    body: Optional[str]
    published_at: datetime
    # Internal enrichments
    # ...
```

**Benefits of Pydantic**:
- **Automatic validation**: Prevents malformed data from entering the system
- **Type safety**: Compile-time error detection
- **Serialization**: Seamless JSON conversion for API responses
- **Documentation**: Self-documenting model structure

### ChromaDB Integration

**Vector Search Capabilities**:
- **Semantic similarity**: Content-based matching beyond keyword search
- **Metadata filtering**: Efficient time-range and source-based queries
- **Hybrid queries**: Combined vector similarity + metadata constraints

**Current Storage**: Local ChromaDB instance for development and testing
**Future Enhancement**: Cloud-based vector databases (Pinecone, Weaviate) with automatic scaling

### MCP Server Integration

The platform includes a **Model Context Protocol (MCP) server** that enables AI tool integration. This was successfully tested with Claude Desktop App, allowing natural language queries like:
- "Show me critical security incidents from this week"
- "What are the latest AWS outages?"
- "Get me the top 20 most relevant IT events"

## User Interface

### Streamlit Web Application

**Technology Choice Rationale**:
- **Rapid prototyping**: Fast development iteration
- **Built-in interactivity**: Parameter adjustment without backend changes
- **Data visualization**: Native support for charts and tables
- **Low resource overhead**: Minimal additional infrastructure

**Key Features**:
- **Parameter tuning**: Real-time adjustment of α and decay_param
- **Source filtering**: Toggle specific news sources
- **Time range selection**: Flexible date range filtering
- **Export capabilities**: CSV download of filtered results

## API Design

### FastAPI Framework Selection

**Technical Advantages**:
- **Automatic documentation**: OpenAPI/Swagger integration
- **Type validation**: Pydantic model integration
- **Async support**: High-concurrency request handling
- **Modern Python**: Leverages latest Python type hints

### Core Endpoints

**Ingestion Endpoint** (`POST /ingest`):
- Accepts both batch and streaming data
- Unified processing for scheduled polling and external API calls
- Automatic embedding generation and storage

**Retrieval Endpoint** (`GET /retrieve`):
- Configurable hybrid scoring parameters
- Metadata filtering (time range, source, etc.)
- Deterministic ordering for test reproducibility

**Admin Endpoints**:
- `/admin/status`: System health monitoring
- `/admin/poll/{source}`: Manual polling triggers
- `/admin/stats`: Ingestion metrics and performance data

## Validation and Testing Strategy

### System Validation Approach

**Challenge**: Defining "relevance" for IT managers is inherently subjective and context-dependent.

**Current Approach**:
1. **Mock data generation**: Created synthetic dataset representing various event types
2. **Parameter tuning**: Iterative adjustment of α and decay_param values
3. **Manual validation**: Verification that critical events rank higher than informational ones

**Future Benchmark Development**:
- **Labeled dataset**: Curated examples of high/medium/low relevance events
- **A/B testing framework**: Comparative evaluation of different scoring approaches
- **User feedback integration**: IT manager input on ranking quality
- **Domain expert validation**: Security and operations team input on event criticality

### Test Coverage

**Unit Tests**: Each component tested in isolation
- Data fetchers with mocked HTTP responses
- Adapters with known data formats
- Scoring algorithms with controlled inputs

For future work, the following tests could be added:

**Integration Tests**: End-to-end workflow validation
- Source polling and ingestion pipelines
- API endpoint functionality
- Database operations and queries

**Performance Tests**: Scalability validation
- Ingestion rate under load
- Query response times with large datasets
- Memory usage patterns

## Engineering Practices and Development Process

### Code Quality and Maintainability

**Development Tools**:
- **uv**: Modern Python package management for reproducible environments
- **ruff**: Fast linting and formatting for consistent code style
- **pytest**: Comprehensive test coverage with fixtures and mocking
- **Makefile**: Simplified development commands and CI/CD integration

**Design Principles Applied**:
- **Dependency injection**: Repository pattern enables easy testing and backend switching
- **Configuration-driven**: YAML-based source management reduces code coupling
- **Type safety**: Full type hints throughout the codebase
- **Error handling**: Comprehensive exception handling with proper logging

### AI-Assisted Development Workflow

Throughout this project, I extensively leveraged AI tools while maintaining architectural oversight:

**AI Tools Used**:
- **Cursor IDE**: Code generation with custom rules and project context
- **Claude Desktop App**: Architecture discussion and problem exploration
- **Gemini**: Secondary validation and alternative perspectives
- **Context7 MCP**: Up-to-date documentation access for AI tools

**Effective AI Collaboration Patterns**:
- **Clear scope definition**: Detailed requirements prevent AI from generating unfocused solutions
- **Iterative refinement**: Multiple rounds of generation and feedback
- **Cross-validation**: Using multiple AI tools to verify approaches
- **Human architectural oversight**: Maintaining big-picture vision while delegating implementation details

**Lessons Learned**:
- **AI excels at**: Exploratory ideation, following detailed specifications, generating boilerplate code
- **AI struggles with**: System-wide coherence, long-term architectural decisions, ambiguous requirements
- **Success factors**: Precise instruction writing, clear problem scoping, iterative development approach

## Scalability Analysis: Handling High-Frequency Updates

### Current Architecture Limitations

With **hundreds of news channels** sending **high-frequency updates**, the current architecture would face several bottlenecks:

1. **Embedding computation**: Sequential processing during ingestion
2. **Single-threaded polling**: APScheduler job limitations
3. **Memory constraints**: In-memory storage limitations
4. **Database write contention**: ChromaDB concurrent update handling

### Proposed Scaling Architecture

#### 1. **Microservices Decomposition**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Fetcher  │ -> │  Message Queue   │ -> │ Embedding       │
│   Services      │    │  (Redis/Kafka)   │    │ Processor       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │ <- │   Vector Store   │ <- │  Event Ingester │
│   (Load Bal.)   │    │   (Pinecone)     │    │   Workers       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

#### 2. **Specialized Source Processors**
- **Custom processors per source**: Optimized parsing and transformation logic
- **Parallel processing**: Independent scaling of different source types
- **Smart batching**: Efficient bulk operations for high-volume sources

#### 3. **Pre-computed Embeddings Pipeline**
- **Async embedding generation**: Decoupled from ingestion critical path
- **Batch processing**: GPU-optimized embedding computation
- **Caching layer**: Redis-based embedding cache for duplicate content

#### 4. **Infrastructure Scaling Components**
- **Message queues**: Redis Streams or Apache Kafka for event distribution
- **Load balancers**: Distribute API requests across multiple instances
- **Auto-scaling**: Kubernetes-based compute scaling for embedding workloads
- **CDN integration**: Geographic distribution of API responses

#### 5. **Data Management Strategy**
- **Time-based partitioning**: Automatic archival of older events
- **Source prioritization**: Quality-based resource allocation
- **Rate limiting**: Per-source ingestion rate controls

## False Alarm and Fake News Detection

### Multi-layered Detection Strategy

#### 1. **Source Credibility Scoring**
- **Reputation tracking**: Historical accuracy assessment per source
- **Authority verification**: Cross-reference with established IT sources
- **Update frequency analysis**: Identify sources with suspicious posting patterns

#### 2. **Content Validation Pipeline**
- **Cross-source verification**: Corroborate events across multiple sources
- **Timeline consistency**: Detect events that contradict established timelines
- **Technical accuracy**: Validate technical details against known configurations
- **Language pattern analysis**: Identify AI-generated or template-based content

#### 3. **Anomaly Detection System**
- **Volume anomalies**: Sudden spikes in event reporting from specific sources
- **Sentiment analysis**: Detect emotionally manipulative content
- **Keyword clustering**: Identify coordinated misinformation campaigns
- **Behavioral patterns**: Unusual source publication patterns

#### 4. **Community Validation**
- **Expert review system**: IT professional verification of critical events
- **Crowdsourced validation**: User feedback on event accuracy
- **Authority confirmation**: Direct verification with service providers


## Future Work and Enhancements


1. **Enhanced source configuration**: More granular polling and filtering controls
2. **Improved embeddings**: Domain-specific model fine-tuning for IT content
3. **Advanced ranking and filtering**: Source-specific decay rates and impact weighting
4. **Performance optimization**: Async processing and caching improvements
5. **Machine learning integration**: Automated event classification and impact assessment ans status classification
6. **Personalization**: User-specific relevance scoring based on their infrastructure
7. **Advanced analytics**: Trend analysis and predictive alerting
8. **Integration ecosystem**: Plugins for popular IT management platforms
9. **AI-powered insights**: Automated root cause analysis and recommendation generation
10. **Federated learning**: Privacy-preserving model improvement across organizations
11. **Real-time collaboration**: Multi-team incident coordination features
12. **Predictive modeling**: Forecasting infrastructure issues based on event patterns

## Conclusion

This IT Newsfeed Platform represents a thoughtful balance between immediate usability and long-term scalability. The architecture prioritizes clear separation of concerns, extensive configurability, and robust error handling while maintaining the flexibility to evolve with changing requirements.

The hybrid relevance + recency scoring system addresses the core challenge of information prioritization for IT managers, while the modular design enables rapid adaptation to new data sources and requirements. The extensive use of AI tools in development demonstrates modern engineering practices while maintaining human oversight of architectural decisions.

The system is production-ready for small to medium deployments while providing clear scaling paths for enterprise use cases involving hundreds of sources and high-frequency updates.