## Why

AI is evolving at a rapid pace, and staying current with developments in AI agents and agent skills requires continuous monitoring of signals from multiple communities. Technical discussions happen across Hacker News, Reddit (r/MachineLearning, r/LocalLLaMA), and GitHub — not any single platform. This system automates discovery and surfacing of the most relevant AI content from these free, open sources, replacing manual browsing with structured, continuous intelligence.

## What Changes

- Introduce an automated multi-source AI news research pipeline that periodically fetches posts from Hacker News, Reddit, and GitHub
- Filter and rank posts by relevance to AI, AI agents, and agent skills using a local keyword weight scoring layer
- Store structured results in a persistent database with deduplication
- Expose a dashboard/API for browsing, searching, and subscribing to curated news feeds
- Send digest notifications (email or webhook) with top stories on a configurable schedule

## Capabilities

### New Capabilities

- `multi-source-fetcher`: Connects to Hacker News (Algolia API), Reddit (JSON API), and GitHub (REST API) to fetch posts and discussions by keyword and subreddit/topic. Handles rate limits, pagination, and per-source authentication.
- `relevance-scorer`: Scores and classifies posts by relevance to AI, AI agents, and agent skills using a local TF-IDF + keyword weight model (no external API). Returns a numeric score (0–10), structured labels, and an `is_relevant` boolean flag.
- `news-store`: Persists fetched and scored posts to a database with deduplication (by `source` + `external_id`), timestamps, and metadata. Supports querying by topic, date, score, and source.
- `digest-notifier`: Generates periodic digests of top-ranked posts and delivers them via email or webhook on a configurable schedule.
- `news-api`: REST API exposing endpoints to list, search, and filter curated news items. Supports pagination, topic filtering, and source filtering.
- `news-dashboard`: Web UI for browsing, searching, and exploring the latest AI news from multiple sources.
- `ai-summarizer`: Uses Google Gemini API (free tier) to generate Traditional Chinese (zh-TW) summaries for relevant posts and assembles them into a structured daily Markdown report grouped by topic. Gated by `GEMINI_API_KEY`; gracefully disabled if key is absent.

### Modified Capabilities

- None

## Impact

- **External dependencies**: Hacker News Algolia API (no auth), Reddit JSON API (no auth for read-only), GitHub REST API (optional token for higher rate limits), database (PostgreSQL or SQLite), email/webhook provider (optional)
- **Infrastructure**: Requires a scheduler (cron), a backend API server, and a frontend host
- **APIs introduced**: `/api/news`, `/api/news/:id`, `/api/digest/trigger`
- **Data privacy**: Only public posts are processed; no user credentials stored
