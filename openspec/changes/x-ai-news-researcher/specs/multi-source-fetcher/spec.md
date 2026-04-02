## ADDED Requirements

### Requirement: Fetch stories from Hacker News by keyword

The system SHALL query the Hacker News Algolia Search API (`https://hn.algolia.com/api/v1/search`) using a configurable set of AI-related keywords. Each query run SHALL fetch up to `HN_FETCH_LIMIT` posts (default: 100) sorted by date descending. No authentication is required.

#### Scenario: Successful keyword fetch
- **WHEN** the scheduler triggers a fetch job
- **THEN** the fetcher queries the Algolia HN API with each configured keyword
- **AND** returns post objects with `external_id` (objectID), `author_handle` (author), `content` (title + story_text), `url`, `posted_at` (created_at), `source = "hackernews"`

#### Scenario: Empty results
- **WHEN** the Algolia API returns zero hits for a query
- **THEN** the fetcher returns an empty list without raising an error

#### Scenario: Algolia API error
- **WHEN** the Algolia API returns a non-2xx response for three consecutive requests
- **THEN** the fetcher logs an error and skips this source for the current cycle without failing the pipeline

> **Known limitation**: Algolia HN API does not publish a hard rate limit. The fetcher operates conservatively at one request per second to avoid implicit throttling.

#### Scenario: HN fetcher stores community votes
- **WHEN** an HN post is fetched from the Algolia API
- **THEN** `points` is populated from `hit["points"]` (integer, may be 0 for new posts)

---

### Requirement: Fetch posts from Reddit subreddits

The system SHALL fetch recent posts from a configurable list of subreddits using the Reddit public JSON API (`https://www.reddit.com/r/{subreddit}/new.json`). Default subreddits: `MachineLearning`, `LocalLLaMA`, `singularity`, `artificial`. Each subreddit fetch SHALL return up to `REDDIT_FETCH_LIMIT` posts per cycle (default: 100).

All requests to the Reddit API SHALL include a custom `User-Agent` header in the format `ai-news-researcher/1.0 (research bot)`. Using default library User-Agents (e.g. `python-httpx/x.y`) will result in 403 responses from Reddit.

Keyword-based search via `reddit.com/search.json` is treated as a secondary, best-effort source due to inconsistent availability without authentication. The primary source SHALL be subreddit `/new.json` feeds.

#### Scenario: Fetch new posts from subreddit
- **WHEN** a subreddit is configured
- **THEN** the fetcher requests `/r/{subreddit}/new.json?limit=100` with the custom User-Agent header
- **AND** returns post objects with `external_id` (Reddit post id), `author_handle` (author), `content` (title + selftext), `url` (permalink), `posted_at` (created_utc), `source = "reddit"`

#### Scenario: Fetcher sends custom User-Agent
- **WHEN** any request is made to the Reddit API
- **THEN** the `User-Agent` header is set to `ai-news-researcher/1.0 (research bot)`

#### Scenario: Subreddit not found or private
- **WHEN** a configured subreddit returns 404 or 403
- **THEN** the fetcher logs a warning and skips that subreddit without failing the entire job

#### Scenario: Reddit keyword search (secondary)
- **WHEN** keyword search mode is enabled via `REDDIT_KEYWORDS` env var
- **THEN** the fetcher queries `https://www.reddit.com/search.json?q={keyword}&sort=new` with the custom User-Agent
- **AND** treats non-200 responses as non-fatal and skips to the next keyword

---

### Requirement: Fetch GitHub repository activity

The system SHALL fetch two types of GitHub signals:

1. **Recently-created high-star repos**: Search for AI repos created in the last 30 days with growing stars using:
   `https://api.github.com/search/repositories?q={keyword}+language:python+created:>{date-30days}&sort=stars&order=desc`

2. **New releases from monitored repos**: Poll `/repos/{owner}/{repo}/releases/latest` for a configurable list of AI projects (e.g., `langchain-ai/langchain`, `microsoft/autogen`, `ollama/ollama`, `ggerganov/llama.cpp`)

> **Note on rate limits**: The GitHub Search API has a stricter rate limit than the general REST API:
> - **Unauthenticated**: 10 requests/minute
> - **Authenticated**: 30 requests/minute
>
> This is separate from the general REST API limit (60 req/h unauthenticated, 5000 req/h authenticated). The fetcher MUST space search requests by at least 6 seconds in unauthenticated mode to stay within the 10 rpm limit.

#### Scenario: Fetch recently-created high-star repositories
- **WHEN** the scheduler triggers a fetch job
- **THEN** the fetcher searches GitHub for repos created within the last 30 days matching AI keywords
- **AND** returns post objects with `external_id` (repo full_name), `author_handle` (owner login), `content` (repo description + topics), `url` (html_url), `posted_at` (created_at), `source = "github"`

#### Scenario: Fetch new release from monitored repo
- **WHEN** a monitored repo publishes a new release since the last fetch cycle
- **THEN** the fetcher creates a post from the release with `content` = release body (truncated to 1000 chars), `url` = release html_url, `posted_at` = published_at, `source = "github"`

#### Scenario: GitHub unauthenticated Search API back-off
- **WHEN** `GITHUB_TOKEN` is not configured
- **THEN** the fetcher sleeps at least 6 seconds between consecutive Search API calls to stay within the 10 rpm limit

#### Scenario: GitHub authenticated uses token header
- **WHEN** `GITHUB_TOKEN` is configured
- **THEN** the fetcher includes `Authorization: Bearer {token}` on every request, enabling 30 rpm for Search API calls

#### Scenario: GitHub Search rate limit header signals exhaustion
- **WHEN** the GitHub API response contains `X-RateLimit-Remaining: 0` and `X-RateLimit-Resource: search`
- **THEN** the fetcher reads `X-RateLimit-Reset`, waits until reset, then retries the request

---

### Requirement: Rate limit handling for all sources

The system SHALL respect each source's rate limits by reading response headers and backing off when limits are approached.

#### Scenario: Reddit 429 Too Many Requests
- **WHEN** Reddit returns a 429 response with a `Retry-After` header
- **THEN** the fetcher waits for the specified duration before retrying

#### Scenario: GitHub general rate limit exhausted
- **WHEN** the GitHub API returns `X-RateLimit-Remaining: 0`
- **THEN** the fetcher reads `X-RateLimit-Reset`, waits until reset, then retries

#### Scenario: Repeated failures from any source
- **WHEN** any source returns three consecutive errors (4xx or 5xx)
- **THEN** the fetcher logs an error, skips the current source for this cycle, and continues with remaining sources

---

### Requirement: Paginated fetch

Each source adapter SHALL follow pagination until the per-source limit is reached or no more pages exist.

#### Scenario: Hacker News pagination
- **WHEN** the Algolia API response includes results and `HN_FETCH_LIMIT` is not yet reached
- **THEN** the fetcher increments the `page` parameter and fetches the next page

#### Scenario: Reddit pagination
- **WHEN** the Reddit API response includes `data.after` token and `REDDIT_FETCH_LIMIT` is not yet reached
- **THEN** the fetcher appends `&after={token}` to fetch the next page

#### Scenario: GitHub pagination
- **WHEN** the GitHub API response includes a `Link: <url>; rel="next"` header and `GITHUB_FETCH_LIMIT` is not yet reached
- **THEN** the fetcher follows the next-page URL

---

### Requirement: Deduplication at fetch time

The system SHALL not return posts already stored, identified by the `(source, external_id)` pair. It SHALL check the news store before passing results downstream.

> **Known limitation (v1)**: Cross-source deduplication (e.g., the same story appearing on both HN and Reddit) is not performed. The same story may appear multiple times in the feed from different sources. Content-fingerprint dedup is deferred to v2.

#### Scenario: Post already in store
- **WHEN** a fetched post's `(source, external_id)` already exists in the news store
- **THEN** the fetcher excludes it from the output list

#### Scenario: New post
- **WHEN** a fetched post's `(source, external_id)` does not exist in the news store
- **THEN** the fetcher includes it in the output list for scoring

---

### Requirement: Unified post schema

All source adapters SHALL map their source-specific response fields to a shared `SourcePost` dataclass before returning results to the pipeline.

```
SourcePost:
  source: str           # "hackernews" | "reddit" | "github"
  external_id: str      # source-specific unique ID
  author_handle: str
  content: str          # title + body, truncated to 2000 chars
  url: str              # original article / resource URL
  discussion_url: str | None  # link to community discussion thread (HN only)
  points: int | None    # community votes: HN points, Reddit score, GitHub stars
  posted_at: datetime   # UTC
```

#### Scenario: HN fetcher populates discussion_url and points
- **WHEN** a Hacker News post is fetched
- **THEN** `url` is set to the linked article URL (or HN item URL if no external link)
- **AND** `discussion_url` is set to `https://news.ycombinator.com/item?id={objectID}`
- **AND** `points` is set to `hit["points"]` from the Algolia response

#### Scenario: Reddit fetcher populates points, discussion_url is null
- **WHEN** a Reddit post is fetched
- **THEN** `points` is set to `post["data"]["score"]` (net upvotes)
- **AND** `discussion_url` is `None` (the `url` field already points to the Reddit thread)

#### Scenario: GitHub fetcher populates points, discussion_url is null
- **WHEN** a GitHub repository post is fetched
- **THEN** `points` is set to `repo["stargazers_count"]`
- **AND** `discussion_url` is `None`

---

### Requirement: Source configuration via environment

| Variable | Default | Description |
|----------|---------|-------------|
| `HN_KEYWORDS` | `ai agent,LLM,RAG,MCP,multi-agent,AutoGen,LangChain` | Comma-separated HN search keywords |
| `HN_FETCH_LIMIT` | `100` | Max posts per HN fetch cycle |
| `REDDIT_SUBREDDITS` | `MachineLearning,LocalLLaMA,singularity,artificial` | Comma-separated subreddit names |
| `REDDIT_KEYWORDS` | _(empty)_ | Optional comma-separated Reddit search keywords (secondary) |
| `REDDIT_FETCH_LIMIT` | `100` | Max posts per subreddit per fetch cycle |
| `GITHUB_MONITORED_REPOS` | `langchain-ai/langchain,microsoft/autogen,ollama/ollama,ggerganov/llama.cpp` | Repos to watch for new releases |
| `GITHUB_KEYWORDS` | `ai agent,llm,rag` | Keywords for GitHub recently-created repo search |
| `GITHUB_FETCH_LIMIT` | `30` | Max repos per GitHub keyword search |
| `GITHUB_TOKEN` | _(empty)_ | Optional token; raises Search API limit from 10 rpm to 30 rpm |
