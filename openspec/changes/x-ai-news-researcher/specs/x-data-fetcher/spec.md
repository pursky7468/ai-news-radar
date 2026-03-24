## ADDED Requirements

### Requirement: Fetch posts by keyword query
The system SHALL query the X API v2 recent search endpoint using a configurable set of keywords and hashtags related to AI, AI agents, and agent skills (e.g., `#AI`, `#AIAgent`, `agent skills`, `LLM`, `Claude`, `GPT`). Each query run SHALL fetch up to 100 posts per keyword group.

#### Scenario: Successful keyword fetch
- **WHEN** the scheduler triggers a fetch job
- **THEN** the fetcher calls the X API v2 recent search endpoint with the configured keyword query
- **AND** returns a list of post objects including post ID, author handle, content, URL, and posted_at timestamp

#### Scenario: Empty results
- **WHEN** the X API returns zero results for a query
- **THEN** the fetcher returns an empty list without raising an error

### Requirement: Fetch posts from monitored accounts
The system SHALL support a configurable list of X account handles to monitor (e.g., `@AnthropicAI`, `@OpenAI`, `@LangChainAI`). It SHALL fetch recent posts from each monitored account using the X API v2 user timeline endpoint.

#### Scenario: Fetch from monitored account
- **WHEN** a monitored account handle is configured
- **THEN** the fetcher retrieves up to 50 recent posts from that account per fetch cycle

#### Scenario: Account not found
- **WHEN** a configured account handle does not exist or is suspended
- **THEN** the fetcher logs a warning and skips that account without failing the entire job

### Requirement: Rate limit handling
The system SHALL respect X API v2 rate limits by tracking remaining request quota from response headers. When the quota is exhausted, it SHALL pause and retry after the reset window (as indicated by `x-rate-limit-reset` header).

#### Scenario: Rate limit reached mid-job
- **WHEN** the X API returns a 429 Too Many Requests response
- **THEN** the fetcher reads the reset timestamp from the response header
- **AND** waits until the reset time before retrying the request

#### Scenario: Repeated rate limit failures
- **WHEN** the fetcher receives three consecutive 429 responses for the same request
- **THEN** it logs an error, skips the current query, and continues with the next one

### Requirement: Paginated fetch using continuation tokens
The X API v2 recent search and user timeline endpoints return a `next_token` in the response metadata when more results exist beyond the current page. The fetcher SHALL follow pagination tokens until either the configured per-query limit is reached or no `next_token` is returned.

#### Scenario: Results span multiple pages
- **WHEN** the X API response includes a `next_token`
- **AND** the fetched count has not yet reached the per-query limit (100 for keywords, 50 for accounts)
- **THEN** the fetcher issues a follow-up request with `pagination_token=<next_token>` and appends results

#### Scenario: Single page of results
- **WHEN** the X API response has no `next_token`
- **THEN** the fetcher returns the results from that single page without additional requests

### Requirement: Deduplication at fetch time
The system SHALL not return posts that have already been stored (by X post ID) in the current fetch cycle. It SHALL check the news store for existing post IDs before passing results downstream.

#### Scenario: Post already in store
- **WHEN** a fetched post ID already exists in the news store
- **THEN** the fetcher excludes it from the output list

#### Scenario: New post
- **WHEN** a fetched post ID does not exist in the news store
- **THEN** the fetcher includes it in the output list for scoring
