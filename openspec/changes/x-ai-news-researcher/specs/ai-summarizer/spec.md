## ADDED Requirements

### Requirement: Generate Chinese (zh-TW) summaries for relevant posts

The system SHALL use the Google Gemini API to generate a Traditional Chinese (zh-TW) summary (≤100 characters) for each relevant post. Summaries are generated on-demand or on a scheduled basis and assembled into a structured daily report.

This feature is **optional and gated by `GEMINI_API_KEY`**. If the key is absent, all summarization endpoints return `503 Service Unavailable` and the scheduled job is skipped without error.

#### Scenario: Summary generated for a single post
- **WHEN** a relevant post is submitted to the summarizer
- **THEN** the system calls the Gemini API with the post's `content`, `source`, and `url`
- **AND** returns a Traditional Chinese summary of ≤100 characters
- **AND** if the Gemini call fails, the system falls back to the post's first 50 characters of content (untranslated)

#### Scenario: Gemini API key not configured
- **WHEN** `GEMINI_API_KEY` is not set
- **THEN** the summarization step is skipped
- **AND** a warning is logged: `"GEMINI_API_KEY not set — AI summarizer disabled"`

#### Scenario: Gemini API rate limit reached
- **WHEN** the Gemini API returns HTTP 429
- **THEN** the system waits 60 seconds and retries once
- **AND** if the retry also fails, falls back to the untranslated excerpt

---

### Requirement: Assemble daily report

The system SHALL assemble individual post summaries into a structured Markdown report in Traditional Chinese, grouped by label category (`ai-agent`, `ai-model`, `ai-tool`, `other`).

#### Scenario: Report assembled from summaries
- **WHEN** summaries for N posts are ready
- **THEN** the report is structured as:
  ```
  # AI 新聞每日彙整 — YYYY-MM-DD
  **共 N 篇相關文章**

  ## 🤖 AI Agent
  - **[post title or first 60 chars]** (`HN` | 342 pts)
    {Chinese summary}
    🔗 [原文](url) | [討論](discussion_url)  ← HN only shows discussion link

  ## 🧠 AI 模型
  ...

  ## 🛠 AI 工具
  ...

  ## 其他
  ...
  ```
- **AND** the report is persisted to the `reports` table

#### Scenario: No relevant posts available
- **WHEN** there are no `is_relevant=True` posts since the last report
- **THEN** no report is generated and the job completes without error

---

### Requirement: Persist generated reports

The system SHALL store each generated report in a `reports` table with the following fields: `id`, `generated_at` (UTC), `content` (Markdown text), `post_count` (integer), `model_used` (string, e.g. `gemini-2.0-flash`).

#### Scenario: Report saved
- **WHEN** a report is successfully generated
- **THEN** it is inserted into the `reports` table with correct metadata

---

### Requirement: API endpoints for report access

#### `POST /api/summary/generate`
- **Auth**: Requires `X-API-Key`
- **WHEN** called
- **THEN** generates a new report from the latest `SUMMARY_POST_LIMIT` relevant posts (default: 20) and returns the report content

#### `GET /api/summary/latest`
- **Auth**: Requires `X-API-Key`
- **WHEN** called
- **THEN** returns the most recently generated report, or `404` if none exists

#### Scenario: Report generation while key is missing
- **WHEN** `POST /api/summary/generate` is called without `GEMINI_API_KEY` configured
- **THEN** HTTP 503 is returned with `{"detail": "AI summarizer not configured"}`

---

### Requirement: Scheduled report generation

The system SHALL support automatically generating a daily report on a configurable cron schedule (default: daily at 08:05 UTC, 5 minutes after the digest job). This can be enabled/disabled independently of the digest.

#### Scenario: Scheduled generation fires
- **WHEN** the cron fires at the configured time and `GEMINI_API_KEY` is set
- **THEN** a new report is generated and persisted

#### Scenario: Key not configured at schedule time
- **WHEN** the cron fires but `GEMINI_API_KEY` is absent
- **THEN** the job is silently skipped (no error, no report)

---

### Requirement: Source configuration via environment

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | _(empty)_ | Google AI Studio API key; feature disabled if absent |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `SUMMARY_POST_LIMIT` | `20` | Max posts per report |
| `SUMMARY_SCHEDULE` | `5 8 * * *` | Cron for auto-generation (08:05 UTC daily) |
