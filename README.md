# **IT News Aggregation Platform**

A scalable, real-time newsfeed platform that aggregates and filters IT-related events from multiple public sources, providing ranked and searchable news specifically relevant to IT managers. This project is a response to the Nexthink AI Engineer take-home assessment.

## **Overview**

This system is architected to continuously fetch IT-related news, apply intelligent filtering to isolate high-signal content (major outages, CVEs, etc.), and store events in a persistent, searchable vector database. A key feature is the asynchronous processing pipeline, which generates text embeddings for semantic search without blocking ingestion requests. The platform exposes a clean REST API for both ingestion and retrieval, with dynamic ranking capabilities.

## **Key Features**

* **Asynchronous Ingestion:** The `/ingest` endpoint provides immediate acknowledgment by delegating heavy processing (like embedding generation) to background workers.
* **Multi-Source Aggregation:** Extensible adapter pattern for various data sources (CISA KEV, vendor status pages, etc.).
* **Intelligent Filtering:** A multi-factor scoring model filters content for IT manager relevance, minimizing false positives.
* **Semantic Vector Search:** ChromaDB-powered similarity search using content embeddings with built-in persistence.
* **Dynamic Ranking:** Balances importance and recency with configurable weights exposed via the API.
* **Production-Ready Practices:** Type-safe, tested, and scalable architecture using modern tools.

## **System Requirements**

* Python 3.13+
* 8GB RAM (recommended for embedding model processing)
* ~500MB storage (for ChromaDB database and indices)

**Core Dependencies:** FastAPI, Pydantic, ChromaDB, Sentence-Transformers, Ruff, pytest.

## **Installation**

```bash
# Clone the repository
git clone <repository-url>
cd newsfeed_platform

# Install dependencies using uv (recommended)
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

## **Quick Start**

**1. Start the Server**

```bash
# Run in development mode with auto-reload
uvicorn app.main:app --reload
```

**2. API Usage**

* **Ingest Events**

  ```sh
  curl -X POST "http://localhost:8000/ingest" \
    -H "Content-Type: application/json" \
    -d '[{"id": "cve-2024-1234", "source": "cisa-kev", "title": "Critical RCE Vulnerability", "body": "...", "published_at": "2025-07-30T10:00:00Z"}]'
  ```

* **Retrieve Filtered Events (Default Ranking)**

  ```sh
  curl "http://localhost:8000/retrieve"
  ```

* **Retrieve Filtered Events (Custom Ranking)**

  ```sh
  curl "http://localhost:8000/retrieve?importance_weight=0.8&recency_weight=0.2"
  ```

## **Architecture**

The system uses a simplified, asynchronous pipeline with ChromaDB as the single source of truth for both persistence and vector search.

**Core Design Patterns:**

* **Adapter Pattern:** Handles various data source formats (JSON, RSS, etc.).
* **Repository Pattern:** Abstracts ChromaDB operations, separating business logic from persistence.
* **Background Task Processing:** Ensures ingestion API remains non-blocking.

**Data Flow Pipeline:**

1. **Ingestion:** `/ingest` endpoint receives raw events, validates them with Pydantic models, and stores them in **ChromaDB** with a `status` of "processing". It immediately returns a `200 OK`.
2. **Background Processing:** A `FastAPI.BackgroundTask` is triggered. It queries ChromaDB for unprocessed events using metadata filters.
3. **Enhancement:** The background task generates embeddings, calculates an initial importance score, and updates the event's metadata in ChromaDB, changing its `status` to "processed".
4. **Indexing:** ChromaDB automatically handles vector indexing and persistence - no separate index management needed.
5. **Retrieval:** The `/retrieve` endpoint queries ChromaDB for processed events using metadata filters, applying the ranking logic (importance × recency) to the results before returning them.

**Technology Stack:**

* **API:** FastAPI
* **Data Validation:** Pydantic v2
* **Database & Vector Search:** ChromaDB (unified persistence and vector search)
* **Embeddings:** Sentence-Transformers (`all-MiniLM-L6-v2` model)
* **Code Quality:** Ruff 
* **Testing:** pytest

## **Key Assumptions**

* **MVP Scope (4-10 hours):**
    * **Asynchronous Processing:** Handled by `FastAPI.BackgroundTasks`, sufficient for the MVP. A full-scale solution would use Celery/Redis.
    * **Single Database:** ChromaDB serves as both the source of truth for event data and the vector search engine, simplifying the architecture.
    * **Single-Instance Deployment:** Designed for a single-node deployment.
* **Content Filtering:**
    * **Target Audience:** IT managers and security professionals.
    * **Importance Algorithm:** Based on a weighted score from source credibility, keyword matching (e.g., "outage", "CVE"), and pattern detection (e.g., CVE identifiers).
* **Ranking Algorithm:**
    * **Formula:** `Final Score = (Importance Score * W_i) + (Recency Score * W_r)`
    * **Default Weights:** Importance (70%), Recency (30%). These are configurable via API parameters.
    * **Deterministic Tie-breaking:** In case of a score tie, items are sorted by `published_at` (desc) then `id` (asc) for stable ordering.