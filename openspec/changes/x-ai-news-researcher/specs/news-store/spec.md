## ADDED Requirements

### Requirement: Persist posts with full metadata
The system SHALL store each post with the following fields: `x_post_id` (unique), `author_handle`, `content`, `url`, `posted_at`, `fetched_at`, `relevance_score`, `is_relevant`, `labels` (JSONB array), `digest_sent` (boolean, default false).

#### Scenario: Insert new post
- **WHEN** a new post with a unique `x_post_id` is submitted for storage
- **THEN** it is inserted into the `posts` table with all provided fields populated

#### Scenario: Duplicate post insert
- **WHEN** a post with an existing `x_post_id` is submitted
- **THEN** the system performs an upsert, updating `relevance_score`, `labels`, and `is_relevant` if they have changed, without creating a duplicate row

### Requirement: Query posts by relevance and topic
The system SHALL support querying stored posts filtered by `is_relevant`, `labels` (contains any of), `posted_at` range, and `relevance_score` minimum. Results SHALL be sortable by `posted_at` descending or `relevance_score` descending.

#### Scenario: Filter by label
- **WHEN** a query specifies label `ai-agent`
- **THEN** only posts whose `labels` array contains `ai-agent` are returned

#### Scenario: Filter by date range
- **WHEN** a query specifies `posted_at` between two timestamps
- **THEN** only posts within that range are returned

#### Scenario: Filter by minimum score
- **WHEN** a query specifies `min_score = 7`
- **THEN** only posts with `relevance_score >= 7` are returned

### Requirement: Mark posts as digest-sent
The system SHALL support updating the `digest_sent` flag to true for a list of post IDs after they have been included in a digest notification.

#### Scenario: Mark digest sent
- **WHEN** the digest notifier successfully sends a digest containing a set of post IDs
- **THEN** all those post IDs have `digest_sent` set to true in the store

#### Scenario: Query unsent posts for digest
- **WHEN** the digest notifier queries for posts not yet sent
- **THEN** only posts where `digest_sent = false` and `is_relevant = true` are returned

### Requirement: Track last successful fetch time
The system SHALL record the timestamp of the most recently completed fetch cycle in a `system_state` table (key-value store with a single row keyed `last_fetch_at`). This value is updated by `FetchPipeline` after each successful fetch-score-store cycle and read by the health endpoint.

#### Scenario: Fetch cycle completes
- **WHEN** a fetch pipeline cycle finishes without fatal error
- **THEN** `system_state.last_fetch_at` is updated to the current UTC timestamp

#### Scenario: No fetch has run yet
- **WHEN** the health endpoint is called before any fetch has completed
- **THEN** `last_fetch_at` is returned as `null`

### Requirement: Database schema migration on startup
The system SHALL automatically apply any pending database migrations on service startup using a migration tool (Alembic). It SHALL NOT overwrite or drop existing data during migration.

#### Scenario: First-time startup
- **WHEN** the service starts against an empty database
- **THEN** all tables are created and the service starts successfully

#### Scenario: Migration already applied
- **WHEN** the service starts and all migrations are already applied
- **THEN** no changes are made and the service starts normally
