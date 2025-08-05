# Field Analysis Summary

## Overview
This document summarizes the detailed field analysis of live news sources to understand their data structures, field types, and value ranges for extending the NewsEvent model.

## Key Findings

### 1. Common Fields Across Sources (14 fields found)

**High-Value Fields for NewsEvent Extension:**

#### Status Fields:
- **`status`** (str, enum-like)
  - **GitHub**: `["resolved"]`
  - **Cloudflare**: `["resolved", "identified"]`
  - **Atlassian**: `["resolved", "postmortem"]`
  - **Description**: Current status (e.g., investigating, resolved)

- **`impact`** (str, enum-like) - **CRITICAL FOR RANKING**
  - **GitHub**: `["minor", "major", "none"]`
  - **Cloudflare**: `["minor", "none", "major"]`
  - **Atlassian**: `["none", "minor", "major", "critical"]`
  - **Description**: Impact level (e.g., minor, major, critical)

#### Timestamp Fields:
- **`created_at`** (str) - Creation timestamp
- **`updated_at`** (str) - Last update timestamp
- **`started_at`** (str) - Start timestamp
- **`resolved_at`** (str) - Resolution timestamp
- **`monitoring_at`** (str/None) - Monitoring start timestamp

#### Content Fields:
- **`incident_updates`** (list) - List of incident updates with detailed information
- **`components`** (list) - Affected components/services
- **`shortlink`** (str) - Short URL link to the incident

#### Metadata Fields:
- **`id`** (str) - Unique identifier for the item
- **`name`** (str) - Human-readable name or title
- **`page_id`** (str) - Reference to parent page
- **`reminder_intervals`** (None) - Reminder configuration

### 2. Source-Specific Field Patterns

#### Status Pages (GitHub, Cloudflare, Atlassian):
- **Consistent Structure**: All use similar incident-based structure
- **Impact Levels**: All have impact fields with similar value ranges
- **Status Values**: Vary by source but generally include "resolved"
- **Components**: List of affected services/components
- **Incident Updates**: Rich content with status changes and descriptions

#### RSS Feeds (TechCrunch):
- **Standard RSS Fields**: title, description, link, pubDate, guid
- **Content Rich**: Detailed descriptions and URLs
- **No Impact/Status**: No built-in impact or status fields

### 3. Impact Field Analysis - Critical for Ranking

**Value Ranges by Source:**
- **GitHub**: `["minor", "major", "none"]`
- **Cloudflare**: `["minor", "none", "major"]`
- **Atlassian**: `["none", "minor", "major", "critical"]`

**Impact Hierarchy:**
1. **`critical`** - Highest priority (Atlassian only)
2. **`major`** - High priority (all sources)
3. **`minor`** - Medium priority (all sources)
4. **`none`** - Low priority (all sources)

### 4. Status Field Analysis

**Value Ranges by Source:**
- **GitHub**: `["resolved"]` (all incidents are resolved)
- **Cloudflare**: `["resolved", "identified"]`
- **Atlassian**: `["resolved", "postmortem"]`

**Status Hierarchy:**
1. **`investigating`** - Active issue (not in current data)
2. **`identified`** - Issue identified, working on fix
3. **`resolved`** - Issue resolved
4. **`postmortem`** - Post-incident analysis

### 5. Components Field Analysis

**Structure**: List of component objects with:
- `id`: Component identifier
- `name`: Component name (e.g., "Git Operations", "API Requests")
- `status`: Component status (e.g., "operational", "partial_outage")
- `description`: Component description

**Common Components Found:**
- Git Operations
- API Requests
- Issues
- Pull Requests
- Actions
- Webhooks
- Packages
- Pages
- Codespaces
- Copilot

### 6. Incident Updates Field Analysis

**Structure**: List of update objects with:
- `id`: Update identifier
- `status`: Update status
- `body`: Detailed description of the update
- `created_at`: Update timestamp
- `affected_components`: Components affected by this update

**Content Quality**: Rich descriptions with technical details, root cause analysis, and resolution steps.

## Recommendations for NewsEvent Extension

### 1. Essential Fields to Add:

```python
class NewsEvent(BaseModel):
    # Existing fields
    id: str
    source: str
    title: str
    body: str = ""
    published_at: datetime
    
    # New essential fields
    status: Optional[str] = None  # Current status
    impact_level: Optional[str] = None  # Impact level (critical/major/minor/none)
    url: Optional[str] = None  # Link to the incident/article
    short_url: Optional[str] = None  # Short link
```

### 2. Extended Fields for Rich Content:

```python
class NewsEvent(BaseModel):
    # ... existing and essential fields ...
    
    # Extended fields
    affected_components: Optional[List[str]] = None  # List of affected services
    incident_updates: Optional[List[Dict]] = None  # Detailed updates
    created_at: Optional[datetime] = None  # Creation timestamp
    updated_at: Optional[datetime] = None  # Last update timestamp
    resolved_at: Optional[datetime] = None  # Resolution timestamp
    started_at: Optional[datetime] = None  # Start timestamp
```

### 3. Impact-Based Ranking Enhancement:

```python
def calculate_impact_score(impact_level: str) -> float:
    """Calculate score based on impact level"""
    impact_scores = {
        "critical": 20.0,
        "major": 15.0,
        "minor": 8.0,
        "none": 2.0
    }
    return impact_scores.get(impact_level, 5.0)
```

### 4. Status-Based Filtering:

```python
def is_active_incident(status: str) -> bool:
    """Check if incident is still active"""
    active_statuses = ["investigating", "identified", "monitoring"]
    return status in active_statuses
```

## Implementation Strategy

### Phase 1: Essential Extensions
1. Add `status`, `impact_level`, `url` fields to NewsEvent
2. Update adapters to extract these fields
3. Enhance ranking algorithm with impact-based scoring

### Phase 2: Rich Content Extensions
1. Add `affected_components`, `incident_updates` fields
2. Implement content enrichment for status pages
3. Add component-based filtering

### Phase 3: Advanced Features
1. Implement status-based filtering
2. Add temporal analysis (created_at, resolved_at)
3. Build component-specific alerts

## Data Quality Observations

### Strengths:
- **Consistent Impact Levels**: All status pages use similar impact hierarchies
- **Rich Component Data**: Detailed information about affected services
- **Temporal Tracking**: Multiple timestamp fields for incident lifecycle
- **Status Progression**: Clear status progression from investigating to resolved

### Challenges:
- **Source Variations**: Different status values across sources
- **Content Enrichment**: Status pages need incident updates for full context
- **RSS Limitations**: RSS feeds lack built-in impact/status fields

### Opportunities:
- **Impact-Based Ranking**: Use impact levels for intelligent prioritization
- **Component Filtering**: Filter by specific services/components
- **Status Tracking**: Track incident lifecycle and resolution times
- **Cross-Source Normalization**: Normalize impact levels across sources 