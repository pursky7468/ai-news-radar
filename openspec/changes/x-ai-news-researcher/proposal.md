## Why

AI is evolving at a rapid pace, and staying current with developments in AI agents and agent skills requires continuous monitoring of real-time social signals. X (Twitter) is the primary platform where AI researchers, engineers, and thought leaders share breaking news, papers, and insights. This system automates the discovery and surfacing of the most relevant and newest AI-related content from X, replacing manual browsing with structured, continuous intelligence.

## What Changes

- Introduce an automated X research pipeline that periodically fetches posts from X using the X API (or scraping layer)
- Filter and rank posts by relevance to AI, AI agents, and agent skills using an LLM scoring layer
- Store structured results in a persistent database with deduplication
- Expose a dashboard/API for browsing, searching, and subscribing to curated news feeds
- Send digest notifications (email or webhook) with top stories on a configurable schedule

## Capabilities

### New Capabilities

- `x-data-fetcher`: Connects to X API / scraping layer to fetch posts by keyword, hashtag, and account. Handles rate limits, pagination, and authentication.
- `relevance-scorer`: Scores and classifies posts by relevance to AI, AI agents, and agent skills using a local TF-IDF + keyword weight model (no external API). Returns a numeric score (0–10), structured labels, and an `is_relevant` boolean flag.
- `news-store`: Persists fetched and scored posts to a database with deduplication, timestamps, and metadata. Supports querying by topic, date, and score threshold.
- `digest-notifier`: Generates periodic digests of top-ranked posts and delivers them via email or webhook on a configurable schedule.
- `news-api`: REST API exposing endpoints to list, search, and filter curated news items. Supports pagination and topic filtering.
- `news-dashboard`: Web UI for browsing, searching, and exploring the latest AI news sourced from X.

### Modified Capabilities

- None

## Impact

- **External dependencies**: X API v2 (Bearer Token auth), Claude API (Anthropic), database (PostgreSQL or SQLite), email/webhook provider (SendGrid or custom)
- **Infrastructure**: Requires a scheduler (cron or task queue like Celery/BullMQ), a backend API server, and a frontend host
- **APIs introduced**: `/api/news`, `/api/news/:id`, `/api/digest/trigger`
- **Data privacy**: Only public X posts are processed; no user credentials stored
