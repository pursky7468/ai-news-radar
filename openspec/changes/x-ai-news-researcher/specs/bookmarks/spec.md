# Bookmarks 規格

> 狀態：v2 Phase C — 待實作（Phase A 穩定後啟動）
> 設計決策：`design.md` § 14, § 15
> 任務清單：`tasks.md` § 19

---

## ADDED Requirements

### Requirement: Article bookmark with personal note

The system SHALL allow users to save articles to a personal bookmark list with an optional text note. Bookmarks SHALL be stored in a dedicated `bookmarks` table, isolated from the scoring, digest, and briefing pipelines.

**Controlled by feature flag**: `FEATURES["bookmarks"]`. When `False`, the bookmark router is not registered and no bookmark endpoints are available.

**DB Schema**:
```sql
CREATE TABLE bookmarks (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  note       TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_bookmarks_article_id ON bookmarks(article_id);
```

#### Scenario: Create bookmark without note
- **WHEN** `POST /api/bookmarks` is called with `{"article_id": 42}`
- **THEN** a bookmark record is created with `note=null`
- **AND** the response includes the created bookmark with HTTP 201

#### Scenario: Create bookmark with note
- **WHEN** `POST /api/bookmarks` is called with `{"article_id": 42, "note": "investigate for RAG pipeline"}`
- **THEN** the bookmark is created with the provided note text

#### Scenario: Duplicate bookmark
- **WHEN** `POST /api/bookmarks` is called for an `article_id` that is already bookmarked
- **THEN** HTTP 409 is returned with message `"Article already bookmarked"`

#### Scenario: Article not found
- **WHEN** `POST /api/bookmarks` is called with an `article_id` that does not exist in `posts`
- **THEN** HTTP 404 is returned with message `"Article not found"`

---

### Requirement: List and search bookmarks

#### Scenario: List all bookmarks
- **WHEN** `GET /api/bookmarks` is called with no parameters
- **THEN** all bookmarks are returned ordered by `created_at` descending
- **AND** each bookmark includes the full article data (title, url, source, summary_zh, points)

#### Scenario: Search bookmarks by keyword
- **WHEN** `GET /api/bookmarks?q=RAG` is called
- **THEN** only bookmarks where the article `title` or `note` contains "RAG" (case-insensitive) are returned

---

### Requirement: Delete bookmark

#### Scenario: Delete existing bookmark
- **WHEN** `DELETE /api/bookmarks/7` is called and bookmark 7 exists
- **THEN** the bookmark is deleted and HTTP 204 is returned
- **AND** the underlying article in `posts` is NOT deleted

#### Scenario: Delete non-existent bookmark
- **WHEN** `DELETE /api/bookmarks/9999` is called and the bookmark does not exist
- **THEN** HTTP 404 is returned

---

### Requirement: Dashboard bookmark UI

#### Scenario: Bookmark button on PostCard
- **WHEN** a user views the news feed
- **THEN** each PostCard displays a bookmark icon (unfilled = not bookmarked, filled = bookmarked)
- **WHEN** the user clicks the unfilled icon
- **THEN** `POST /api/bookmarks` is called and the icon toggles to filled
- **WHEN** the user clicks the filled icon
- **THEN** `DELETE /api/bookmarks/{id}` is called and the icon toggles to unfilled

#### Scenario: Bookmarks page
- **WHEN** the user navigates to `/bookmarks`
- **THEN** a list of all bookmarked articles is shown with note text, article title, source badge, and delete button
- **WHEN** the user types in the search box
- **THEN** the list is filtered client-side by article title or note content

---

### Requirement: Personalization context injection

**Controlled by**: `USER_CONTEXT` environment variable (no feature flag needed — gracefully ignored when empty).

#### Scenario: USER_CONTEXT is set
- **WHEN** `USER_CONTEXT="I am building a RAG pipeline with LangChain"` is configured
- **AND** the daily briefing is generated
- **THEN** the LLM system prompt includes: `"使用者當前工作 context：I am building a RAG pipeline with LangChain"`
- **AND** the briefing output prioritizes content relevant to RAG and LangChain

#### Scenario: USER_CONTEXT is empty
- **WHEN** `USER_CONTEXT` is not set or is an empty string
- **THEN** the system prompt is unchanged from the v1 baseline (no degradation)

#### Scenario: USER_CONTEXT does not affect scoring
- **WHEN** `USER_CONTEXT` is set
- **THEN** the `RelevanceScorer` output is unchanged — personalization only affects the LLM briefing prompt, not the numeric scores stored in the database
