# ArXiv Fetcher 規格

> 狀態：v2 Phase A — 待實作
> 設計決策：`design.md` § 9
> 任務清單：`tasks.md` § 17.3

---

## ADDED Requirements

### Requirement: Fetch AI/ML papers from ArXiv

The system SHALL fetch recent papers from ArXiv using the free Atom feed API (`http://export.arxiv.org/api/query`), filtering by AI/ML categories. The fetcher SHALL implement the existing `SourceFetcher` interface and return `SourcePost` objects compatible with the existing scoring pipeline.

**Controlled by feature flag**: `FEATURES["arxiv_fetcher"]`. When `False`, the fetcher is not registered in `MultiSourceFetcher` and no ArXiv requests are made.

#### Scenario: Fetch papers from AI/ML categories
- **WHEN** the scheduler triggers a fetch job and `FEATURES["arxiv_fetcher"]` is `True`
- **THEN** the fetcher queries ArXiv Atom API with `search_query=cat:cs.AI OR cat:cs.LG OR cat:cs.CL AND {keywords}`
- **AND** returns at most `ARXIV_MAX_RESULTS` (default: 50) papers
- **AND** maps each paper to `SourcePost` with:
  - `source = "arxiv"`
  - `external_id = arxiv_id` (e.g., `"2403.12345"`)
  - `url = abstract_url` (e.g., `https://arxiv.org/abs/2403.12345`)
  - `content = title + ". " + abstract` (truncated to 2000 chars)
  - `posted_at = published` (UTC)
  - `points = None` (no community voting on ArXiv)
  - `discussion_url = None`

#### Scenario: Pre-filter by publication date
- **WHEN** a paper was published more than 7 days ago
- **THEN** the fetcher excludes it from the output list
- **Rationale**: Limits daily volume and keeps content fresh; historical ArXiv papers can be added via `add_article` MCP tool

#### Scenario: ArXiv API error
- **WHEN** the ArXiv API returns a non-2xx response or times out
- **THEN** the fetcher logs an error and returns an empty list without failing the pipeline
- **AND** the `MultiSourceFetcher` continues with remaining sources

#### Scenario: Deduplication
- **WHEN** a fetched paper's `(source="arxiv", external_id)` already exists in the news store
- **THEN** the fetcher excludes it from the output list

#### Scenario: Empty category results
- **WHEN** ArXiv returns zero results for the configured categories and keywords
- **THEN** the fetcher returns an empty list without raising an error

---

### Requirement: ArXiv source configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_CATEGORIES` | `cs.AI,cs.LG,cs.CL` | Comma-separated ArXiv category codes |
| `ARXIV_MAX_RESULTS` | `50` | Maximum papers per fetch cycle (cap to control token usage) |
| `ARXIV_KEYWORDS` | _(inherits from `HN_KEYWORDS`)_ | Additional keyword filter for ArXiv query string |

---

### Requirement: Scoring compatibility

ArXiv papers SHALL pass through the existing `RelevanceScorer` without modification. Since `points=None` for all ArXiv papers, the points bonus in the scorer (`min((points or 0) / 100, 3.0)`) evaluates to 0, which is correct behavior — paper relevance is driven purely by keyword content.

#### Scenario: ArXiv paper scored by existing scorer
- **WHEN** an ArXiv `SourcePost` enters the scoring pipeline
- **THEN** the scorer evaluates `content` (title + abstract) against the keyword weight model
- **AND** assigns a `relevance_score` between 0 and 10 normally
- **AND** applies no points bonus (since `points=None`)
