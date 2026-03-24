## ADDED Requirements

### Requirement: List news items with filtering
The system SHALL expose a `GET /api/news` endpoint that returns a paginated list of stored posts. It SHALL support the following query parameters: `label` (filter by label), `min_score` (integer), `from_date` (ISO 8601), `to_date` (ISO 8601), `is_relevant` (boolean), `q` (full-text keyword search against post content), `sort` (`score_desc` or `date_desc`, default `date_desc`), `page` (default 1), `per_page` (default 20, max 100).

#### Scenario: Default list request
- **WHEN** `GET /api/news` is called with no parameters
- **THEN** the 20 most recent posts are returned sorted by `posted_at` descending

#### Scenario: Filter by label and min score
- **WHEN** `GET /api/news?label=ai-agent&min_score=7` is called
- **THEN** only posts labeled `ai-agent` with score >= 7 are returned

#### Scenario: Pagination
- **WHEN** `GET /api/news?page=2&per_page=10` is called
- **THEN** the second page of 10 results is returned with a `total` count in the response body

#### Scenario: Keyword search
- **WHEN** `GET /api/news?q=multi-agent` is called
- **THEN** only posts whose content contains `multi-agent` (case-insensitive) are returned

### Requirement: Get single news item
The system SHALL expose a `GET /api/news/{id}` endpoint that returns a single post by its internal database ID. If the post does not exist, it SHALL return HTTP 404.

#### Scenario: Post found
- **WHEN** `GET /api/news/42` is called and post 42 exists
- **THEN** the full post object is returned with HTTP 200

#### Scenario: Post not found
- **WHEN** `GET /api/news/9999` is called and post 9999 does not exist
- **THEN** HTTP 404 is returned with a JSON error message

### Requirement: Trigger digest manually
The system SHALL expose a `POST /api/digest/trigger` endpoint that immediately runs the digest generation and delivery pipeline. It SHALL return a summary of how many posts were included and which delivery channels were used.

#### Scenario: Digest triggered successfully
- **WHEN** `POST /api/digest/trigger` is called
- **THEN** the digest job runs synchronously (or enqueued and a job ID returned)
- **AND** the response includes `posts_included`, `email_sent` (boolean), `webhook_sent` (boolean)

#### Scenario: No posts available for digest
- **WHEN** `POST /api/digest/trigger` is called with no unsent relevant posts
- **THEN** HTTP 200 is returned with `posts_included: 0` and no notifications sent

### Requirement: Health check endpoint
The system SHALL expose a `GET /api/health` endpoint that returns the current status of the service, database connectivity, and last successful fetch time.

#### Scenario: Healthy service
- **WHEN** `GET /api/health` is called and the DB is reachable
- **THEN** HTTP 200 is returned with `status: "ok"`, `db: "connected"`, and `last_fetch_at` timestamp

#### Scenario: DB unreachable
- **WHEN** `GET /api/health` is called and the DB connection fails
- **THEN** HTTP 503 is returned with `status: "degraded"` and `db: "disconnected"`

### Requirement: API authentication
All endpoints except `GET /api/health` SHALL require a valid API key passed via the `X-API-Key` header. Invalid or missing keys SHALL return HTTP 401.

#### Scenario: Valid API key
- **WHEN** a request includes a valid `X-API-Key` header
- **THEN** the request is processed normally

#### Scenario: Missing or invalid API key
- **WHEN** a request is made without or with an invalid `X-API-Key` header
- **THEN** HTTP 401 is returned with a JSON error message
