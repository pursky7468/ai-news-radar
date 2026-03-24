## Context

There is no existing codebase for this system — this is a greenfield production service. The system will connect to X (Twitter) via the X API v2 to fetch public posts, score them for relevance to AI/agents/agent skills using a local TF-IDF + keyword weight model, persist results, and surface them via an API and dashboard.

Key constraints:
- X API v2 free tier has strict rate limits (500k tweets/month, 1 request/15s on Basic plan); the design must be rate-limit-aware
- Scoring must be fast, free, and require no external API calls
- The system must be deployable on a single server or small cloud VM for initial production

Stakeholders: internal AI research team consuming the news feed.

## Goals / Non-Goals

**Goals:**
- Continuously fetch new X posts matching AI/agent/agent-skill keywords and accounts
- Score and classify posts by relevance using a local TF-IDF + keyword weight model (no external API)
- Persist deduplicated posts in a queryable database
- Expose a REST API for consuming curated news
- Provide a lightweight web dashboard for browsing results
- Send periodic digest emails or webhook notifications

**Non-Goals:**
- Fetching non-public X content or requiring user OAuth login
- Real-time streaming (polling is sufficient for v1)
- Multi-platform support (Reddit, HN, LinkedIn) — X only for now
- Full-text search with Elasticsearch — basic SQL filtering is sufficient for v1
- Mobile app

## Decisions

### 1. X Data Access: API v2 with fallback scraping

**Decision**: Use X API v2 (Bearer Token, app-only auth) as the primary data source. Use `recent search` endpoint with keyword queries. If rate limits are hit, back off and retry with exponential delay.

**Rationale**: API v2 is the only supported, ToS-compliant method. Free/Basic tier covers research-scale volumes.

**Alternatives considered**:
- Scraping without API: Fragile, ToS violation risk, harder to maintain.
- Third-party X data providers (e.g., Brandwatch): Expensive, overkill for v1.

---

### 2. Relevance Scoring: TF-IDF + keyword weight model

**Decision**: Score each post locally using a weighted keyword scoring approach combined with TF-IDF term weighting. Maintain a tiered keyword dictionary: high-weight terms (e.g., `ai agent`, `agent skill`, `MCP`, `RAG`, `LLM`, `multi-agent`) score higher than generic terms (e.g., `AI`, `model`). The final score (0–10) is derived from the sum of matched term weights, normalized and clamped. Assign category labels based on which term groups fire. Cache scores by post ID to avoid re-scoring.

**Rationale**: No external API dependency, zero cost, runs in-process with sub-millisecond latency per post. Sufficient accuracy for surfacing AI/agent news given that the input is already filtered to AI-adjacent X posts. Can be improved iteratively by tuning the keyword weights without a model retraining cycle.

**Alternatives considered**:
- Claude API (LLM scoring): Accurate but adds cost, latency, and an external dependency. Deferred to v2 if precision needs improvement.
- Fine-tuned classifier: Requires labeled dataset; overkill for v1.
- Pure regex: No weighting or scoring, only binary match.

---

### 3. Storage: PostgreSQL with simple schema

**Decision**: Use PostgreSQL. Schema: `posts` table (id, x_post_id unique, author, content, url, posted_at, fetched_at, relevance_score, labels jsonb, digest_sent bool).

**Rationale**: PostgreSQL is reliable, supports JSONB for flexible labels, and handles the expected volume (thousands of posts/day) with ease.

**Alternatives considered**:
- SQLite: Simpler but poor concurrency; limits horizontal scaling.
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

**Rationale**: FastAPI is async-native, auto-generates OpenAPI docs, and Python aligns with scikit-learn (TF-IDF scorer) and Tweepy (X API client) ecosystem.

---

### 6. Development Methodology: Test-Driven Development (TDD)

**Decision**: All backend components (NewsStore, XDataFetcher, RelevanceScorer, DigestNotifier, REST API) and frontend components (NewsFeed, FilterBar, SearchBox, DigestButton) SHALL be developed following the Red-Green-Refactor cycle:
1. **Red** — Write a failing test that defines the expected behavior
2. **Green** — Write the minimum code needed to make the test pass
3. **Refactor** — Clean up without breaking tests

Backend test stack: `pytest` + `pytest-asyncio` + `pytest-cov` + `factory-boy` (fixtures). Unit tests use an in-memory SQLite database; integration tests use a dedicated PostgreSQL test container. External calls (Tweepy, SMTP, webhooks) are mocked at the boundary. Frontend test stack: `Jest` + `React Testing Library`. API calls are mocked with `msw` (Mock Service Worker).

**Rationale**: The pipeline has several failure modes (rate limits, dedup, scoring edge cases, delivery errors) that are difficult to catch manually. Writing tests first forces precise specification of each behavior before implementation, and ensures regressions are caught immediately. The keyword scorer in particular benefits from test-first development since scoring logic is easy to miscalibrate.

**Alternatives considered**:
- Test-after (write tests post-implementation): Tests tend to be written to match what was built rather than what was specified; misses edge cases.
- No automated tests: Acceptable for throwaway scripts, not for a production pipeline.

---

### 7. Frontend: Next.js (minimal)

**Decision**: A minimal Next.js app consumes the REST API and renders the news feed dashboard.

**Rationale**: Fast to build, supports SSR for SEO if needed, easy to deploy on Vercel or alongside the backend.

## Risks / Trade-offs

- **X API rate limits** → Mitigation: Implement exponential backoff, track request quotas in DB, alert when approaching monthly cap.
- **Scoring false positives** → Mitigation: Tune keyword weights iteratively; raise the relevance threshold if digest quality is low.
- **X API policy changes** → Mitigation: Abstract the data fetcher behind an interface so alternate sources can be plugged in.
- **Duplicate posts across query runs** → Mitigation: Unique constraint on `x_post_id`; upsert on conflict.
- **Single point of failure (one server)** → Mitigation: Acceptable for v1; add health checks and systemd auto-restart.

## Migration Plan

1. Provision PostgreSQL instance and run schema migrations
2. Configure X API credentials as environment variables (no Claude API key needed)
3. Deploy FastAPI backend (with APScheduler) via Docker or systemd
4. Deploy Next.js dashboard
5. Verify first fetch cycle and scoring pipeline end-to-end
6. Enable digest notifier after confirming data quality

**Rollback**: Scheduler can be disabled by stopping the service. No destructive DB migrations in v1.

## Open Questions

- Should the digest be sent via email (SendGrid) or webhook (Slack/Discord)? → Default to both, configurable per environment.
- What relevance score threshold defines "newsworthy" for the digest? → Start at 7/10, tune after first week of data.
- Should users be able to add custom X accounts to monitor via the API? → Deferred to v2.
