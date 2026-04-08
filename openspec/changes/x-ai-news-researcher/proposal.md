## Why

AI is evolving at a rapid pace, and staying current with developments in AI agents and agent skills requires continuous monitoring of signals from multiple communities. Technical discussions happen across Hacker News, Reddit (r/MachineLearning, r/LocalLLaMA), and GitHub — not any single platform. This system automates discovery and surfacing of the most relevant AI content from these free, open sources, replacing manual browsing with structured, continuous intelligence.

Additionally, this system serves as an **AI Agent knowledge base** — agents can query it during development to find relevant tools, papers, and technical discussions without switching context.

## What Changes

### v1 (Implemented)
- Automated multi-source AI news research pipeline (HN, Reddit, GitHub)
- Keyword weight scoring + relevance classification
- Daily Traditional Chinese briefings via Groq/Gemini
- REST API + Next.js dashboard
- MCP Server with 3 tools for Claude integration

### v2 (Planned — based on user feedback 2026-04-06)
- Add **ArXiv** as a fourth data source (academic papers, cs.AI / cs.LG)
- Add **cross-date full-text search** with date range filtering (P0)
- Add **weekly briefing / trend summary** generation (P1)
- Add **Top 3 algorithmic highlight** per daily digest (P1)
- Expand MCP Server with `get_trending_tools` and `get_weekly_summary` tools (P1)
- Add **article bookmarks + personal notes** (P2)
- Add **lightweight personalization** via `USER_CONTEXT` env var (P2)

## Capabilities

### New Capabilities (v1)

- `multi-source-fetcher`: Connects to Hacker News (Algolia API), Reddit (JSON API), and GitHub (REST API) to fetch posts and discussions by keyword and subreddit/topic. Handles rate limits, pagination, and per-source authentication.
- `relevance-scorer`: Scores and classifies posts by relevance to AI, AI agents, and agent skills using a local TF-IDF + keyword weight model (no external API). Returns a numeric score (0–10), structured labels, and an `is_relevant` boolean flag.
- `news-store`: Persists fetched and scored posts to a database with deduplication (by `source` + `external_id`), timestamps, and metadata. Supports querying by topic, date, score, and source.
- `digest-notifier`: Generates periodic digests of top-ranked posts and delivers them via email or webhook on a configurable schedule.
- `news-api`: REST API exposing endpoints to list, search, and filter curated news items. Supports pagination, topic filtering, and source filtering.
- `news-dashboard`: Web UI for browsing, searching, and exploring the latest AI news from multiple sources.
- `ai-summarizer`: Uses Groq/Gemini to generate Traditional Chinese (zh-TW) summaries and daily Markdown briefings. Gated by API keys; gracefully disabled if absent.
- `llm-agent-integration`: MCP Server exposing `search_ai_news`, `get_daily_report`, `get_posts_by_category` for direct Claude integration.

### New Capabilities (v2 — Planned)

- `arxiv-fetcher`: Fetches AI/ML papers from ArXiv (cs.AI, cs.LG, cs.CL categories) via the free Atom feed API. Pre-filters by keyword before scoring. Max 50 papers/day.
- `full-text-search`: SQLite FTS5 index over `title` + `summary` columns, exposed via expanded `search_ai_news(query, date_from?, date_to?)` MCP tool and dashboard search bar.
- `weekly-briefing`: Automated weekly trend summary generated every Monday by re-using the briefing pipeline with a 7-day aggregation prompt. Output: `briefings/weekly/YYYY-WNN.md`.
- `highlight-scorer`: Composite ranking algorithm (relevance × 0.5 + source weight × 0.3 + recency × 0.2) to select Top 3 articles per daily digest. Coefficients configurable via `config.py`.
- `bookmarks`: User-facing article save + note system. Stored in a new `bookmarks` table, accessible via REST endpoints. Independent of digest and scoring logic.
- `personalization-context`: `USER_CONTEXT` environment variable injected into briefing system prompts to bias summaries toward the user's current work context.

### Modified Capabilities (v2)

- `multi-source-fetcher`: Extended to include ArXiv as a fourth source via `ArxivFetcher` implementing the existing `SourceFetcher` interface.
- `llm-agent-integration`: MCP Server extended with `get_trending_tools(days)` and `get_weekly_summary(week_offset)` tools.
- `news-api`: Extended with bookmark endpoints (`POST /api/bookmarks`, `GET /api/bookmarks`, `DELETE /api/bookmarks/{id}`) and search date range parameters.

## Impact

- **External dependencies**: Hacker News Algolia API (no auth), Reddit JSON API (no auth for read-only), GitHub REST API (optional token), ArXiv Atom API (no auth, free), database (PostgreSQL or SQLite), email/webhook provider (optional)
- **Infrastructure**: Requires a scheduler (cron), a backend API server, and a frontend host
- **APIs introduced (v1)**: `/api/news`, `/api/news/:id`, `/api/digest/trigger`, `/api/summary/reports`
- **APIs introduced (v2)**: `/api/bookmarks`, `/api/weekly-summary`
- **Data privacy**: Only public posts are processed; bookmarks are local to the deployment instance; no user credentials stored
