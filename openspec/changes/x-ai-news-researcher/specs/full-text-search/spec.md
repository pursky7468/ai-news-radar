# Full-Text Search 規格

> 狀態：v2 Phase A — 待實作
> 設計決策：`design.md` § 10
> 任務清單：`tasks.md` § 17.1, § 17.2

---

## ADDED Requirements

### Requirement: Cross-date full-text search via FTS5

The system SHALL support full-text search across all stored articles with optional date range filtering. Search SHALL be performed via SQLite FTS5 (or LIKE fallback when FTS5 flag is disabled) against the `title` and `summary` columns.

**Controlled by feature flag**: `FEATURES["fts_search"]`. When `False`, the existing LIKE-based `q=` search continues to work unchanged (backward compatible).

#### Scenario: FTS5 search with date range
- **WHEN** `GET /api/news?q=RAG&date_from=2026-03-01&date_to=2026-04-01` is called
- **THEN** only posts matching "RAG" in title or summary AND published within the date range are returned
- **AND** results are ranked by FTS5 relevance score descending

#### Scenario: Search without date range (unchanged behavior)
- **WHEN** `GET /api/news?q=RAG` is called without date parameters
- **THEN** all matching posts are returned regardless of date (same as current behavior)

#### Scenario: FTS5 flag disabled — LIKE fallback
- **WHEN** `FEATURES["fts_search"]` is `False`
- **THEN** the system uses the existing LIKE-based search: `WHERE content LIKE '%{q}%'`
- **AND** `date_from` / `date_to` parameters are still applied as SQL date filters

#### Scenario: FTS5 index stays in sync
- **WHEN** a new post is inserted into the `posts` table
- **THEN** the INSERT trigger automatically adds the corresponding row to `articles_fts`
- **WHEN** a post is updated
- **THEN** the UPDATE trigger keeps the FTS index in sync
- **WHEN** a post is deleted
- **THEN** the DELETE trigger removes the corresponding FTS row

---

### Requirement: MCP search tool backward compatibility

The `search_ai_news` MCP tool SHALL be extended with optional `date_from` and `date_to` parameters. All existing callers that omit these parameters SHALL continue to work without modification.

#### Scenario: Existing call without date range
- **WHEN** an agent calls `search_ai_news("streaming LLM")`
- **THEN** behavior is identical to pre-v2: searches all articles without date restriction

#### Scenario: New call with date range
- **WHEN** an agent calls `search_ai_news("RAG tools", date_from="2026-03-01", date_to="2026-04-01")`
- **THEN** only articles within the specified date range are returned

---

### Requirement: DB Migration 006 — FTS5 index

Migration 006 SHALL be applied before any feature flag is enabled. It SHALL be safe to apply to an existing database with data.

#### Scenario: Migration on existing database
- **WHEN** `alembic upgrade head` is run on a database with existing posts
- **THEN** the `articles_fts` virtual table is created and populated from existing `posts` data
- **AND** all three sync triggers (INSERT / UPDATE / DELETE) are installed
- **AND** all existing API endpoints continue to function normally

#### Scenario: Migration rollback
- **WHEN** `alembic downgrade -1` is run
- **THEN** the `articles_fts` virtual table and all three sync triggers are dropped
- **AND** existing posts data is unaffected
