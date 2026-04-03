## ADDED Requirements

> **Design principle**: AI summarization is NOT a standalone pipeline. It is integrated into the
> existing `DigestNotifier` flow. When a digest runs, Gemini summaries are generated per-post,
> cached in the DB, and included in the existing email/webhook delivery channels.

---

### Requirement: Per-post Chinese summary generation

The system SHALL use the Google Gemini API to generate a Traditional Chinese (zh-TW) summary
(≤100 characters) for each relevant post before digest delivery. The summary is cached in a
`summary_zh` column on the `posts` table so the same post is never summarized twice.

This feature is **gated by `GEMINI_API_KEY`**. If the key is absent, summarization is skipped
and digest delivery proceeds with English content only — no error is raised.

#### Scenario: Post without cached summary
- **WHEN** a digest run encounters a relevant post where `summary_zh IS NULL`
- **AND** `GEMINI_API_KEY` is configured
- **THEN** the system calls Gemini with the post content (truncated to 500 chars)
- **AND** stores the returned Chinese text in `posts.summary_zh`
- **AND** waits 4 seconds before the next post to respect free-tier rate limits (15 RPM)

#### Scenario: Post with cached summary
- **WHEN** a digest run encounters a post where `summary_zh` is already populated
- **THEN** the cached value is used directly; no Gemini API call is made

#### Scenario: Gemini API key not configured
- **WHEN** `GEMINI_API_KEY` is absent
- **THEN** summarization step is skipped entirely
- **AND** digest delivery continues with original English content
- **AND** a single warning is logged: `"GEMINI_API_KEY not set — AI summarizer disabled"`

#### Scenario: Gemini API 429 rate limit
- **WHEN** the Gemini API returns HTTP 429
- **THEN** the system waits 60 seconds and retries the same post once
- **AND** if the retry also fails, falls back to the first 50 characters of `content` (untranslated)
- **AND** the `summary_zh` column is NOT updated (retry on next digest run)

#### Scenario: Circuit breaker — repeated failures
- **WHEN** 3 consecutive Gemini API calls fail (any error, not just 429)
- **THEN** the system stops attempting further calls for the current digest batch
- **AND** logs an error: `"Gemini circuit breaker open after 3 failures — skipping remaining posts"`
- **AND** digest delivery continues with whatever summaries were successfully generated

---

### Requirement: Assemble Chinese daily report

After per-post summaries are generated, the system SHALL assemble a structured Markdown report
in Traditional Chinese grouped by label category.

#### Report format
```
# AI 新聞每日彙整 — YYYY-MM-DD
**共 N 篇相關文章**

## 🤖 AI Agent

- **{first 60 chars of content}** (`HN` ▲ 342)
  {summary_zh or fallback excerpt}
  🔗 [原文](url) · [HN 討論](discussion_url)   ← discussion link for HN only

## 🧠 AI 模型
...

## 🛠 AI 工具
...

## 📰 其他
...
```

#### Scenario: Report assembled
- **WHEN** summaries are ready (full or partial)
- **THEN** posts are grouped by their first label
- **AND** the assembled Markdown is persisted to the `reports` table

#### Scenario: No relevant posts
- **WHEN** digest has no posts to process
- **THEN** no report is generated

---

### Requirement: Persist generated reports

The system SHALL store each assembled report in a `reports` table:
`id`, `generated_at` (UTC), `content` (Markdown), `post_count` (int), `model_used` (str).

---

### Requirement: Deliver Chinese summary via existing channels

The existing digest delivery channels SHALL be enhanced to include Chinese content.

#### Email delivery
- **WHEN** `SMTP_HOST` is configured and summaries are available
- **THEN** the email body SHALL include a "中文摘要" section after the existing post list
- **AND** each post entry in the email shows `summary_zh` if available

#### Webhook delivery
- **WHEN** `DIGEST_WEBHOOK_URL` is configured
- **THEN** each post object in the JSON payload SHALL include a `summary_zh` field (string or null)
- **AND** the payload SHALL include a top-level `report_markdown` field with the full assembled report

---

### Requirement: API endpoint for latest report

#### `GET /api/summary/latest`
- **Auth**: Requires `X-API-Key`
- **WHEN** called
- **THEN** returns the most recently generated report as `ReportResponse`
- **AND** returns `404` if no report has been generated yet

> Note: Report generation is triggered by the existing `POST /api/digest/trigger` or the
> scheduled digest job — there is no separate generate endpoint.

---

### Requirement: Source configuration via environment

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | _(empty)_ | Groq API key (recommended, free tier); takes priority over Gemini if both set |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `GEMINI_API_KEY` | _(empty)_ | Google AI Studio API key; used as fallback if `GROQ_API_KEY` is absent |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `SUMMARY_POST_LIMIT` | `20` | Max posts to summarize per digest run |

**Provider priority**: `GROQ_API_KEY` takes precedence. If both are set, Groq is used. If neither is set, summarization is skipped.

---

### Requirement: Groq provider support

The system SHALL support Groq as an alternative AI summarization provider, using the same `summarize_post` interface as Gemini.

#### Scenario: Groq key configured
- **WHEN** `GROQ_API_KEY` is set (regardless of `GEMINI_API_KEY`)
- **THEN** `GroqClient` is used for summarization with the configured `GROQ_MODEL`

#### Scenario: Only Gemini key configured
- **WHEN** `GROQ_API_KEY` is empty and `GEMINI_API_KEY` is set
- **THEN** `GeminiClient` is used as fallback

#### Scenario: Groq 429 rate limit
- **WHEN** Groq API returns HTTP 429
- **THEN** the system waits 60 seconds and retries once
- **AND** if retry fails, falls back to first 50 characters of `content`
