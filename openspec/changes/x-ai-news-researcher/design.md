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

**Non-Goals (v1):**
- Fetching non-public content or requiring user OAuth login
- Real-time streaming (polling is sufficient for v1)
- X (Twitter) / LinkedIn / Mastodon support — three open sources for now
- Full-text search with Elasticsearch — basic SQL filtering is sufficient for v1
- Mobile app

**Goals (v2 — based on user feedback 2026-04-06):**
- Add ArXiv as a fourth data source (cs.AI, cs.LG, cs.CL categories)
- Cross-date full-text search via SQLite FTS5 (no Elasticsearch dependency)
- Weekly trend briefing aggregating 7-day signals
- Top 3 algorithmic daily highlight (composite score ranking)
- Expanded MCP tools for agent use cases (`get_trending_tools`, `get_weekly_summary`)
- Article bookmark + personal notes system
- Lightweight personalization via `USER_CONTEXT` environment variable

**Non-Goals (v2):**
- X / Twitter integration (API cost $100+/month, high noise ratio)
- Multi-tenant user accounts or SaaS identity layer (deferred; `USER_CONTEXT` env var is sufficient for single-user deployments)
- Manual editorial curation — all highlights are algorithm-selected
- Obsidian / Notion export (deferred; search covers the recall use case first)

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

**Decision**: Score each post locally using a keyword weight scoring approach. Maintain a tiered keyword dictionary: high-weight terms (e.g., `ai agent`, `agent skill`, `MCP`, `RAG`, `LLM`, `multi-agent`) score higher than generic terms (e.g., `AI`, `model`). The final score (0–10) is derived from the sum of matched term weights, clamped at 10. Assign category labels based on which term groups fire. Cache scores by post ID to avoid re-scoring.

> **實作說明（2026-04-12 確認）**：IDF 部分未實作。實際公式為：
> `score = min(10, Σ(命中詞 × 權重) + min(社群票數 / 100, 3.0))`
> 設計文件中所有「TF-IDF」描述均指此公式，非標準 TF-IDF 演算法。

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

---

### 8. AI Summarizer: Google Gemini API (free tier)

**Decision**: Use `gemini-2.0-flash` via `google-generativeai` Python SDK to generate Traditional Chinese (zh-TW) summaries of relevant posts. Feature is optional and gated by `GEMINI_API_KEY`.

**Rationale**: Gemini 2.0 Flash offers a free tier (1,500 req/day, 1M tokens/day) sufficient for PoC validation with 20 posts/day. Avoids paid Claude API dependency while validating the summarization workflow. The free quota covers daily operation without cost.

**Report format**: Per-post Chinese summary (≤100 chars) generated individually, then assembled locally into a Markdown report grouped by label. Local assembly avoids a second Gemini call and is more reliable.

**Graceful degradation**: If `GEMINI_API_KEY` is absent or a call fails, the system falls back to an untranslated excerpt. The pipeline never blocks on summarization failure.

**Alternatives considered**:
- Claude API: Most accurate but paid. Deferred until PoC validates the value of AI summarization.
- Ollama (local): Free but requires GPU/RAM; not suitable for lightweight deployment. Can replace Gemini in v2 for offline use.
- Batch summarization (one call for all posts): Simpler but harder to handle partial failures and harder to cache per-post results.

**Rate limit handling**: Gemini free tier is 15 RPM. The system adds a 4-second delay between post-level calls to stay within limits comfortably.

---

## Open Questions

- Should the digest be sent via email (SendGrid) or webhook (Slack/Discord)? → Default to both, configurable per environment.
- What relevance score threshold defines "newsworthy" for the digest? → Start at 7/10, tune after first week of data.
- Should users be able to add custom subreddits or GitHub repos to monitor via the API? → Deferred to v2.

---

## v2 Architecture Decisions

### 9. Fourth Data Source: ArXiv

**Decision**: Add `ArxivFetcher` implementing the existing `SourceFetcher` interface. Fetch from ArXiv Atom API (`export.arxiv.org/api/query`) filtering by categories `cs.AI`, `cs.LG`, `cs.CL`. Cap at `ARXIV_MAX_RESULTS=50` per day to control token usage.

**Rationale**: ArXiv papers are the earliest signal for AI technical advances, predating HN/Reddit discussion by days or weeks. Free API with no auth required. Existing `SourcePost` schema and scoring pipeline accept the output without modification.

**Pre-filter strategy**: Apply keyword filter on `ti:` (title) or `abs:` (abstract) fields in the ArXiv query string before results enter the scoring pipeline. This reduces token consumption significantly.

**Alternatives considered**:
- Semantic Scholar API: More structured but requires registration; ArXiv is simpler.
- arXiv RSS feeds: Limited to 100 entries with no keyword filtering; API is more flexible.

---

### 10. Full-Text Search: SQLite FTS5

**Decision**: Create an `articles_fts` FTS5 virtual table mirroring `title` and `summary` columns. Add database triggers to keep it in sync. Extend `search_ai_news` MCP tool and `GET /api/news?q=` to accept optional `date_from` / `date_to` parameters.

**Rationale**: SQLite FTS5 is built-in, zero infrastructure cost, and sufficient for single-server workloads. No Elasticsearch or external service required. Backward-compatible: existing `q=` parameter continues to work unchanged.

**Migration**: Alembic migration 006 creates the FTS5 virtual table and three sync triggers (INSERT, UPDATE, DELETE).

---

### 11. Weekly Briefing

**Decision**: Add a `WeeklyBriefingGenerator` that re-uses the existing `BriefingGenerator` infrastructure with a 7-day aggregation SQL query and a different system prompt emphasizing trend comparison. Schedule every Monday 08:00 via APScheduler. Output: `briefings/weekly/YYYY-WNN.md`.

**Rationale**: The daily briefing pipeline is already proven. A weekly variant is a prompt + query change, not a new subsystem. Re-using the same LLM client and Markdown output format keeps maintenance overhead near zero.

---

### 12. Top 3 Algorithmic Highlight

**Decision**: Compute a `highlight_score` at briefing generation time using the formula:
```
highlight_score = relevance_score * 0.5
               + source_weight * 0.3   # arxiv=4, github=3, hn=2, reddit=1
               + recency_decay * 0.2   # 1.0 if < 24h, 0.5 if < 48h, 0.0 otherwise
```
Top 3 posts by `highlight_score` are marked as `[⭐ 精選]` in the daily briefing output. Coefficients are configurable in `config.py`.

**Rationale**: No additional LLM call required. Deterministic and auditable. Coefficients in config allow tuning without code changes.

---

### 13. Expanded MCP Tools

**Decision**: Add two new MCP tools to `backend/mcp_server.py`:
- `get_trending_tools(days=7, limit=10)`: matches known tool names from a `known_tools.txt` keyword list against recent articles, returns frequency-ranked list
- `get_weekly_summary(week_offset=0)`: reads the corresponding weekly briefing Markdown file and returns its content

**Rationale**: Both tools are pure read operations over existing data. No new DB schema required. `known_tools.txt` avoids NLP dependency for entity extraction. Backward-compatible: existing three tools unchanged.

---

### 14. Bookmarks

**Decision**: Add a `bookmarks` table with `(id, article_id FK, note TEXT, created_at)`. Expose via:
- `POST /api/bookmarks` — create bookmark with optional note
- `GET /api/bookmarks` — list bookmarks (supports `q=` search)
- `DELETE /api/bookmarks/{id}` — remove bookmark

Dashboard adds a bookmark button to each `PostCard`. No MCP exposure — bookmarks are personal data, not knowledge base content.

**Rationale**: Minimal schema addition. Isolated from all existing scoring, digest, and briefing logic. Provides the "information retention" capability users need most.

---

### 15. Personalization Context (Lightweight)

**Decision**: Read `USER_CONTEXT` environment variable in `BriefingGenerator` and inject it into the LLM system prompt as additional context. No user table, no dynamic scoring changes.

**Rationale**: Solves the core personalization use case (biased briefing toward current work) at near-zero implementation cost. Avoids introducing a user identity layer prematurely.

**Example**:
```bash
USER_CONTEXT="I am currently building a RAG pipeline with LangChain and pgvector"
```

---

### 16. Feature Flags

**Decision**: Add a `FEATURES` dict to `config.py` controlling opt-in for each v2 feature. Default all to `False` during rollout.

```python
FEATURES = {
    "arxiv_fetcher": False,
    "fts_search": False,
    "weekly_briefing": False,
    "highlight_scorer": False,
    "bookmarks": False,
}
```

**Rationale**: Allows safe, incremental rollout. Any feature can be disabled instantly without code deployment if issues arise.

---

### Deployment Order (v2)

1. Alembic migrations (FTS5 index, bookmarks table, url index) — verify existing features unaffected
2. Backend changes with all feature flags `False` — run full regression test suite
3. Enable `fts_search` — monitor 24h
4. Enable `arxiv_fetcher` — monitor token usage
5. Enable `weekly_briefing` + `highlight_scorer`
6. Dashboard UI updates (bookmarks button, search date range) — pure frontend, no backend risk
7. Enable `bookmarks`
