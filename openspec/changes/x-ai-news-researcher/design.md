## Context

There is no existing codebase for this system — this is a greenfield production service. The system will connect to Hacker News (Algolia API), Reddit (JSON API), and GitHub (REST API) to fetch public posts and discussions, score them for relevance to AI/agents/agent skills using a local TF-IDF + keyword weight model, persist results, and surface them via an API and dashboard.

Key constraints:
- All three data sources offer free, unauthenticated (or optionally-authenticated) APIs; no paid plan required
- Scoring must be fast, free, and require no external API calls
- The system must be deployable on a single server or small cloud VM for initial production

Stakeholders: internal AI research team consuming the news feed.

## Goals / Non-Goals

**Goals:**
- Continuously fetch new posts from Hacker News, Reddit, and GitHub matching AI/agent/agent-skill keywords
- Score and classify posts by relevance using a local TF-IDF + keyword weight model (no external API)
- Persist deduplicated posts in a queryable database
- Expose a REST API for consuming curated news
- Provide a lightweight web dashboard for browsing results
- Send periodic digest emails or webhook notifications

**Non-Goals:**
- Fetching non-public content or requiring user OAuth login
- Real-time streaming (polling is sufficient for v1)
- X (Twitter) / LinkedIn / Mastodon support — three open sources for now
- Full-text search with Elasticsearch — basic SQL filtering is sufficient for v1
- Mobile app

## Decisions

### 1. Data Sources: Hacker News + Reddit + GitHub

**Decision**: Use three complementary free data sources:
- **Hacker News** via Algolia Search API (`hn.algolia.com/api/v1/search`) — no auth, keyword search over stories and comments
- **Reddit** via public JSON API (`reddit.com/r/{subreddit}.json`, `reddit.com/search.json`) — no auth for read-only; subreddits: `r/MachineLearning`, `r/LocalLLaMA`, `r/singularity`, `r/artificial`
- **GitHub** via REST API (`api.github.com`) — optional token for 5,000 req/h; fetch trending AI repos, new releases for monitored projects (e.g., LangChain, AutoGen, Ollama, llama.cpp)

**Rationale**: All three sources are free and open, cover different signal types (community discussions vs. code releases), and require no paid subscription. Together they provide better coverage than any single platform.

**Alternatives considered**:
- X (Twitter) API: Requires paid Basic tier ($100/month) for search access. Eliminated.
- arXiv RSS: Good for academic papers but low community signal; can be added in v2.
- Dev.to API: Lower signal-to-noise ratio for AI agent content; deferred.

---

### 2. Relevance Scoring: TF-IDF + keyword weight model

**Decision**: Score each post locally using a weighted keyword scoring approach combined with TF-IDF term weighting. Maintain a tiered keyword dictionary: high-weight terms (e.g., `ai agent`, `agent skill`, `MCP`, `RAG`, `LLM`, `multi-agent`) score higher than generic terms (e.g., `AI`, `model`). The final score (0–10) is derived from the sum of matched term weights, normalized and clamped. Assign category labels based on which term groups fire. Cache scores by post ID to avoid re-scoring.

**Rationale**: No external API dependency, zero cost, runs in-process with sub-millisecond latency per post. Can be improved iteratively by tuning keyword weights without a model retraining cycle.

**Alternatives considered**:
- Claude API (LLM scoring): Accurate but adds cost, latency, and an external dependency. Deferred to v2.
- Fine-tuned classifier: Requires labeled dataset; overkill for v1.
- Pure regex: No weighting or scoring, only binary match.

---

### 3. Storage: PostgreSQL with simple schema

**Decision**: Use PostgreSQL (SQLite for dev). Schema: `posts` table with `source` (enum: `hackernews`, `reddit`, `github`) + `external_id` as the unique key, plus `author_handle`, `content`, `url`, `posted_at`, `fetched_at`, `relevance_score`, `is_relevant`, `labels` (JSONB), `digest_sent`.

**Rationale**: Adding a `source` column allows deduplication across sources (same story may appear on both HN and Reddit) using content fingerprinting. PostgreSQL handles JSONB labels cleanly.

**Alternatives considered**:
- SQLite only: Simpler but poor concurrency; limits horizontal scaling.
- MongoDB: No advantage for this structured data shape.

---

### 4. Scheduler: Cron-based polling with APScheduler

**Decision**: Use APScheduler (Python) to run fetch jobs every 15 minutes and digest jobs on a daily/weekly schedule. No external task queue for v1.

**Rationale**: Simple, self-contained, no Redis/RabbitMQ dependency. Sufficient for single-server deployment.

**Alternatives considered**:
- Celery + Redis: Powerful but heavy; overkill for v1 polling cadence.
- GitHub Actions cron: Stateless, harder to manage secrets and state.

---

### 5. Backend: FastAPI (Python)

**Decision**: FastAPI serves the REST API. The same process hosts the scheduler.

**Rationale**: FastAPI is async-native, auto-generates OpenAPI docs, and Python aligns with scikit-learn (TF-IDF scorer) and HTTPX (async HTTP client for all three source APIs) ecosystem.

---

### 6. Development Methodology: Test-Driven Development (TDD)

**Decision**: All backend components (NewsStore, MultiSourceFetcher, RelevanceScorer, DigestNotifier, REST API) and frontend components (NewsFeed, FilterBar, SearchBox, DigestButton) SHALL be developed following the Red-Green-Refactor cycle.

Backend test stack: `pytest` + `pytest-asyncio` + `pytest-cov` + `factory-boy` (fixtures). External HTTP calls (Algolia, Reddit, GitHub, SMTP, webhooks) are mocked at the boundary using `respx`. Frontend test stack: `Jest` + `React Testing Library` + `msw`.

**Rationale**: The pipeline has several failure modes (rate limits, dedup, scoring edge cases, delivery errors) that are difficult to catch manually. TDD forces precise specification before implementation.

---

### 7. Frontend: Next.js (minimal)

**Decision**: A minimal Next.js app consumes the REST API and renders the news feed dashboard with source badges per post.

**Rationale**: Fast to build, supports SSR for SEO if needed, easy to deploy on Vercel or alongside the backend.

## Risks / Trade-offs

- **Reddit API informal limits** → Mitigation: Respect `Retry-After` headers; default to 1 req/sec; use User-Agent header to avoid blocks.
- **GitHub API rate limits (60 req/h unauthenticated)** → Mitigation: Add optional `GITHUB_TOKEN` env var; fetch only monitored repos, not all of GitHub.
- **Scoring false positives** → Mitigation: Tune keyword weights iteratively; raise the relevance threshold if digest quality is low.
- **Duplicate posts across sources** → Mitigation: Unique constraint on `(source, external_id)`; optional content-hash dedup for cross-source duplicates in v2.
- **Single point of failure (one server)** → Mitigation: Acceptable for v1; add health checks and systemd auto-restart.

## Migration Plan

1. Provision database and run schema migrations
2. Configure optional GitHub token as environment variable (HN and Reddit need no auth)
3. Deploy FastAPI backend (with APScheduler) via Docker or systemd
4. Deploy Next.js dashboard
5. Verify first fetch cycle from all three sources end-to-end
6. Enable digest notifier after confirming data quality

**Rollback**: Scheduler can be disabled by stopping the service. The schema migration from `x_post_id` to `(source, external_id)` is a one-time destructive migration applied at initial deployment; no rollback migration is provided since this is a greenfield service with no production data to preserve.

## Open Questions

- Should the digest be sent via email (SendGrid) or webhook (Slack/Discord)? → Default to both, configurable per environment.
- What relevance score threshold defines "newsworthy" for the digest? → Start at 7/10, tune after first week of data.
- Should users be able to add custom subreddits or GitHub repos to monitor via the API? → Deferred to v2.
