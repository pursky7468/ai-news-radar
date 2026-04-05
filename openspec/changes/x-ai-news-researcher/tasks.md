## 1. Project Setup & Test Infrastructure

- [x] 1.1 Initialize Python project with pyproject.toml (FastAPI, httpx, scikit-learn, APScheduler, SQLAlchemy, Alembic, psycopg2-binary, python-dotenv, PyYAML)
- [x] 1.2 Add test dependencies: pytest, pytest-asyncio, pytest-cov, factory-boy, httpx, respx
- [x] 1.3 Configure pytest.ini: test discovery, asyncio mode, coverage report (fail below 80%)
- [x] 1.4 Create `tests/conftest.py` with shared fixtures: in-memory SQLite engine, test NewsStore, sample post factory
- [x] 1.5 Initialize Next.js project for the dashboard (TypeScript, Tailwind CSS)
- [x] 1.6 Add frontend test dependencies: Jest, React Testing Library, msw (Mock Service Worker)
- [x] 1.7 Configure Jest with jsdom environment and RTL setup file
- [x] 1.8 Create Docker Compose file with services: api, db (PostgreSQL), and dashboard
- [x] 1.9 Create .env.example with all required environment variables (HN/Reddit/GitHub config, DB URL, SMTP config, webhook URL, API key)
- [x] 1.10 Set up Alembic for database migrations

## 2. Database & News Store (TDD)

- [x] 2.0 **[Pre-migration code sweep]** Replace all references to `x_post_id` with `(source, external_id)` pair across the codebase before running any migration. Files updated:
  - `backend/app/models.py` — replaced `x_post_id` column with `source` + `external_id`, added `UniqueConstraint("source", "external_id")`
  - `backend/app/store/news_store.py` — replaced `x_post_id` queries with `(source, external_id)` lookups
  - `backend/app/schemas.py` — replaced `x_post_id: str` with `source: str` + `external_id: str`
  - `backend/app/pipeline/fetch_pipeline.py` — updated log references
  - `backend/tests/conftest.py` — updated `PostFactory` fields
  - `backend/tests/test_news_store.py` — updated `make_post()` helper and all assertions
  - `backend/tests/test_api.py` — updated `_insert_post()` helper
  - `backend/tests/test_pipeline.py` — updated mock fetcher return values
- [x] 2.1 Write tests for NewsStore: upsert, dedup, query filters, source filter, since filter, exists checks, digest, system_state
- [x] 2.2 Alembic migration 002: `batch_alter_table(recreate="always")` drops `x_post_id`, adds `source`+`external_id`, composite unique constraint + source index
- [x] 2.3 Implement `NewsStore.upsert_post` — dedup by (source, external_id)
- [x] 2.4 Implement `NewsStore.query_posts` with label/score/date/source/since/sort params
- [x] 2.5 Implement `NewsStore.mark_digest_sent` and `get_unsent_relevant_posts`
- [x] 2.6 Implement `NewsStore.get_post_by_id`
- [x] 2.6b Implement `NewsStore.exists_by_source_and_external_id(source, external_id) -> bool`
- [x] 2.6c Implement `NewsStore.commit()` — called by FetchPipeline to persist after batch store
- [x] 2.7a Implement `NewsStore.update_last_fetch_at` and `get_last_fetch_at`
- [x] 2.7 Add indexes on `posted_at`, `relevance_score`, `is_relevant`, and `source` columns
- [x] 2.8 Consolidate query builder logic via `_apply_filters()` helper

## 3. Relevance Scorer (TDD)

- [x] 3.1–3.8 All scorer tests and implementation complete (12 tests, 97% coverage)

## 4. Multi-Source Fetcher (TDD)

### 4.0 Interface Design
- [x] 4.0.1 `SourcePost` dataclass: `source`, `external_id`, `author_handle`, `content`, `url`, `posted_at`
- [x] 4.0.2 `MultiSourceFetcher` public interface: single `.fetch() -> list[SourcePost]`

### 4a. Hacker News Fetcher — DONE
- [x] 4a.1–4a.4 `HackerNewsFetcher` complete: Algolia API, pagination, dedup, error handling (6 tests)

### 4b. Reddit Fetcher — DONE
- [x] 4b.1–4b.4 `RedditFetcher` complete: public JSON API, custom User-Agent, 403 skip, 429 retry-after, pagination, dedup (7 tests)

### 4c. GitHub Fetcher — DONE
- [x] 4c.1–4c.4 `GitHubFetcher` complete: repo search, releases, auth token, rate limit sleep, pagination (7 tests)

### 4d. MultiSourceFetcher Orchestrator — DONE
- [x] 4d.1–4d.4 `MultiSourceFetcher.fetch()` delegates to HN+Reddit+GitHub, merges, logs errors; tested via rate limit integration tests

## 5. Digest Notifier (TDD)

- [x] 5.1–5.6 All notifier tests and implementation complete (8 tests, 92% coverage)

## 6. REST API (TDD)

- [x] 6.1 Pydantic schemas updated: `source: str` + `external_id: str` in `Post`
- [x] 6.2 API tests updated + new tests: `test_news_list_filter_by_source`, `test_news_list_filter_by_since`, `test_news_get_by_id_includes_source_field`
- [x] 6.3 API key authentication middleware
- [x] 6.4 `GET /api/health`
- [x] 6.5 `GET /api/news` with `source` + `since` query params
- [x] 6.6 `GET /api/news/{id}`
- [x] 6.7 `POST /api/digest/trigger`
- [x] 6.8 Shared filter logic in NewsStore

## 7. Scheduler & Pipeline (TDD)

- [x] 7.1 Pipeline tests updated to use `MultiSourceFetcher.fetch()` interface
- [x] 7.2 `FetchPipeline` updated: single `fetcher.fetch()` call, `dataclasses.asdict()` conversion, `store.commit()` at end
- [x] 7.3 Structured logging per pipeline stage
- [x] 7.4 APScheduler with fetch job (every 15 min) + digest job (configurable cron)
- [x] 7.5 `start_scheduler()` constructs `HackerNewsFetcher` + `RedditFetcher` + `GitHubFetcher` + `MultiSourceFetcher` from settings
- [x] 7.6 Pipeline steps independently testable

## 8. Dashboard (TDD — Next.js)

- [x] 8.1 API client: `Post` type has `source`+`external_id`; `NewsQueryParams` has `source`+`since`; `fetchNews` passes both params
- [x] 8.2–8.3 `PostCard`: source badge (HN=orange, Reddit=red, GitHub=dark), "View source →" link
- [x] 8.4–8.5 `FilterBar`: source chips (All/HN/Reddit/GitHub) + label chips + score slider (5 tests)
- [x] 8.6–8.7 `SearchBox`: server-side search, `onSearch(q)` callback, 300ms debounce (2 tests)
- [x] 8.8–8.9 `DigestButton`: success/error toast (2 tests)
- [x] 8.10–8.11 `NewsFeed`: `?since=` polling, new-posts banner, renders PostCard list directly (auto-refresh: 2 tests)
- [x] 8.12 Loading skeletons and empty states
- [x] 8.13 Source badge in PostCard sub-component

## 9. Configuration & Deployment

- [x] 9.1 `config.py`: removed `x_bearer_token`/`monitored_accounts`; added `hn_keywords`, `reddit_subreddits`, `github_monitored_repos`, `github_token`, per-source fetch limits + list properties
- [x] 9.2 Dockerfile for FastAPI backend
- [x] 9.3 Dockerfile for Next.js dashboard
- [x] 9.4 Docker Compose with volume and health checks
- [x] 9.5 `scripts/seed_keywords.py` updated: prints HN keywords, Reddit subreddits, GitHub repos/keywords
- [x] 9.6 `README.md` updated: removed X API section, added multi-source config table, updated env vars table, updated seed SQL, updated API query params table

## 10. End-to-End Validation

- [x] 10.1 Full test suite: **84 backend tests pass, 88% coverage** | **17 frontend tests pass, 93% coverage**
- [x] 10.2 Live pipeline run: HN 10 + Reddit 3 + GitHub 4 = 17 posts fetched and stored to dev.db
- [x] 10.3 API endpoints verified: list, source filter, since filter, digest trigger all return correct data
- [x] 10.4 Dashboard visual verification: load feed with source badges, source filter, `?since=` auto-refresh, digest button
- [x] 10.5 Digest webhook test: payload confirmed to include `source` field (verified via local capture server 2026-03-31)
- [x] 10.6 Rate limit integration tests: GitHub `X-RateLimit-Reset` sleep, Reddit `Retry-After` sleep, pipeline partial results, MultiSourceFetcher exception isolation — all covered in `test_rate_limit_integration.py`

---

## 11. HN Dual Links + Community Vote Count (`points`)

> Plan: `C:\Users\User\.claude\plans\hn-dual-links-points.md`

### 11.1 Data layer (backend)
- [x] 11.1.1 `source_post.py` — add `points: int | None = None` + `discussion_url: str | None = None`
- [x] 11.1.2 `hn_fetcher.py` — populate `points=hit.get("points")` + `discussion_url`
- [x] 11.1.3 `reddit_fetcher.py` — populate `points=data.get("score")`
- [x] 11.1.4 `github_fetcher.py` — populate `points=stargazers_count` (repo) / `points=0` (release)
- [x] 11.1.5 `models.py` — add `points = Column(Integer, nullable=True)`
- [x] 11.1.6 `news_store.py` — pass `points=data.get("points")` in `upsert_post`
- [x] 11.1.7 `alembic/versions/003_add_points.py` — new migration, `batch_alter_table(recreate="always")`
- [x] 11.1.8 `tests/conftest.py` — add `points = None` to `PostFactory`

### 11.2 Scorer: `points` bonus
- [x] 11.2.1 `relevance_scorer.py` — add `score = min(10.0, score + min((points or 0) / 100, 3.0))` in `_compute_score`

### 11.3 API schema
- [x] 11.3.1 `schemas.py` — add `points: Optional[int]`; add `discussion_url: Optional[str]` computed via `@model_validator` for HN posts

### 11.4 Frontend
- [x] 11.4.1 `lib/api.ts` — add `points?: number`, `discussion_url?: string` to `Post` interface
- [x] 11.4.2 `components/PostCard.tsx` — dual links (HN: "View article" + "HN discussion"; others: "View source"); `▲ {points}` badge when points > 0

### 11.5 Tests
- [x] 11.5.1 `test_hn_fetcher.py` — assert `points` field populated; missing key → `None`
- [x] 11.5.2 `test_reddit_fetcher.py` — assert `points == score`
- [x] 11.5.3 `test_github_fetcher.py` — assert repo `points == stargazers_count`; release `points == 0`
- [x] 11.5.4 `test_relevance_scorer.py` — 4 new tests: bonus, cap at 3, None as 0, total cap at 10
- [x] 11.5.5 `test_api.py` — `discussion_url` correct for HN; `None` for Reddit/GitHub; `points` round-trips
- [x] 11.5.6 `PostCard.test.tsx` — new file, 7 tests (dual links, points badge, non-HN single link)
- [x] 11.5.7 `mock-data.ts` + `NewsFeed.test.tsx` — add `points`/`discussion_url` to mock; fix label assertion

### 11.6 Migration
- [x] 11.6.1 Run `alembic upgrade head` on dev.db — migration 003 at head

---

## 12. AI Summarizer — Gemini API 中文每日彙整（整合進 DigestNotifier）

> Plan: `C:\Users\User\.claude\plans\gemini-summarizer.md`
> Spec: `openspec/changes/x-ai-news-researcher/specs/ai-summarizer/spec.md`
>
> **設計原則**：不建立獨立 pipeline。Gemini 摘要整合進現有 `DigestNotifier.run()`，
> 透過現有 email/webhook 交付，無 80 秒同步 API 問題。

### 12.1 依賴與設定
- [x] 12.1.1 `pyproject.toml` — 加入 `google-generativeai` + `groq` 依賴
- [x] 12.1.2 `config.py` — 加入 `gemini_api_key`, `gemini_model`, `summary_post_limit`, `groq_api_key`, `groq_model`
- [x] 12.1.3 `.env` — 加入 `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `SUMMARY_POST_LIMIT`

### 12.2 DB Schema（Migration 004）
- [x] 12.2.1 `models.py` — `Post` 加 `summary_zh = Column(Text, nullable=True)`；新增 `Report` model
- [x] 12.2.2 `alembic/versions/004_add_summary.py` — `batch_alter_table(recreate="always")` 加 `summary_zh`；`create_table("reports")`
- [x] 12.2.3 `tests/conftest.py` — `PostFactory` 加 `summary_zh = None`

### 12.3 GeminiClient / GroqClient
- [x] 12.3.1 `backend/app/summarizer/gemini_client.py` — `summarize_post(post) -> str`；retry on 429（sleep 60s, once）；fallback to excerpt on failure
- [x] 12.3.2 `backend/app/summarizer/groq_client.py` — 相同介面；`GROQ_API_KEY` 優先於 Gemini
- [x] 12.3.3 呼叫端負責 `sleep(4)` between calls（15 RPM free tier 安全邊際）

### 12.4 SummaryGenerator
- [x] 12.4.1 `backend/app/summarizer/summary_generator.py` — `summarize_batch(posts)`：per-post call + cache to DB + circuit breaker（3 consecutive failures → stop）
- [x] 12.4.2 `assemble_report(posts, date) -> str`：local Markdown 組裝，依 label 分組，含 points badge + 雙連結（HN only）

### 12.5 ReportStore（加入 NewsStore）
- [x] 12.5.1 `update_post_summary(post_id, summary_zh)` — flush only
- [x] 12.5.2 `save_report(content, post_count, model_used) -> Report` — flush only
- [x] 12.5.3 `get_latest_report() -> Report | None`

### 12.6 DigestNotifier 整合
- [x] 12.6.1 `digest_notifier.py` — `run()` 加入摘要步驟：Groq 優先，fallback Gemini；`summarize_batch` → `assemble_report` → `save_report` → `commit()`
- [x] 12.6.2 Email body 末尾加入「中文摘要」section（含各篇 `summary_zh`）
- [x] 12.6.3 Webhook payload 每個 post 加 `summary_zh` 欄位；頂層加 `report_markdown`

### 12.7 API Schema + Endpoint
- [x] 12.7.1 `schemas.py` — 加 `summary_zh: Optional[str]` 到 `Post`；加 `ReportResponse` schema
- [x] 12.7.2 `backend/app/api/routes/summary.py` — `GET /api/summary/latest`（需 API key；404 if none）
- [x] 12.7.3 `backend/app/main.py` — 註冊 summary router

### 12.8 Tests (TDD)
- [x] 12.8.1 `test_gemini_client.py` — mock SDK；assert summary；assert 429 retry + sleep(60)；assert fallback excerpt
- [x] 12.8.2 `test_summary_generator.py` — mock GeminiClient；assert skips cached posts；assert circuit breaker stops at 3 failures；assert label grouping；assert HN discussion link；assert Reddit no discussion link
- [x] 12.8.3 `test_api.py` — `test_summary_latest_not_found_404`；`test_summary_latest_returns_report`
- [x] 12.8.4 `test_digest_notifier.py` — assert `summarize_batch` called when key set；assert skipped when no key；assert webhook payload has `summary_zh`

### 12.9 End-to-End Validation
- [x] 12.9.1 設定 `GROQ_API_KEY`，觸發 `POST /api/digest/trigger`，確認 `GET /api/summary/latest` 回傳中文報告（model: llama-3.3-70b-versatile）
- [x] 12.9.2 確認報告依 label 分組、HN 雙連結、points badge 顯示正確

---

---

## 13. Report History Browser — 歷史彙整瀏覽（含分類篩選）

> Spec: `specs/news-dashboard/spec.md` (Requirement: Report history browser)
> Spec: `specs/news-api/spec.md` (Requirement: List all reports / Get report by ID)
>
> **設計原則**：分類篩選在前端 parse Markdown section headers（client-side），不異動 DB schema。
> 後端只新增兩支 API endpoint。

### 13.1 Backend — Schema

- [x] 13.1.1 `schemas.py` — `ReportResponse` 加入 `id: int` 欄位
- [x] 13.1.2 `schemas.py` — 新增 `ReportListItem` schema（`id`, `generated_at`, `post_count`, `model_used`，不含 `content`）

### 13.2 Backend — Store

- [x] 13.2.1 `news_store.py` — 新增 `get_reports(limit: int = 50, offset: int = 0) -> list[Report]`，按 `generated_at DESC` 排序
- [x] 13.2.2 `news_store.py` — 新增 `get_report_by_id(report_id: int) -> Report | None`

### 13.3 Backend — API Routes

- [x] 13.3.1 `routes/summary.py` — `GET /api/summary/reports`：回傳 `list[ReportListItem]`
- [x] 13.3.2 `routes/summary.py` — `GET /api/summary/reports/{id}`：回傳 `ReportResponse`；不存在回 404

### 13.4 Backend — Tests

- [x] 13.4.1 `test_api.py` — `test_reports_list_empty`：no reports → `[]`
- [x] 13.4.2 `test_api.py` — `test_reports_list_returns_items`：多筆回傳，按日期降序，不含 `content`
- [x] 13.4.3 `test_api.py` — `test_report_by_id_found`：回傳完整 content
- [x] 13.4.4 `test_api.py` — `test_report_by_id_not_found`：404

### 13.5 Frontend — API Client

- [x] 13.5.1 `lib/api.ts` — `Report` interface 加入 `id: number`
- [x] 13.5.2 `lib/api.ts` — 新增 `ReportListItem` interface（`id`, `generated_at`, `post_count`, `model_used`）
- [x] 13.5.3 `lib/api.ts` — 新增 `fetchReports(): Promise<ReportListItem[]>`
- [x] 13.5.4 `lib/api.ts` — 新增 `fetchReportById(id: number): Promise<Report>`

### 13.6 Frontend — Report Page 重構

- [x] 13.6.1 `app/report/page.tsx` — 載入報告列表，顯示為日期 Pill 列（按 `generated_at DESC`），預設選最新
- [x] 13.6.2 `app/report/page.tsx` — 點選日期 Pill → 載入對應 report（`fetchReportById`）
- [x] 13.6.3 `app/report/page.tsx` — 分類 Tabs：`全部` / `🤖 AI Agent` / `🧠 AI 模型` / `🛠 AI 工具` / `📰 其他`
- [x] 13.6.4 `app/report/page.tsx` — 分類篩選邏輯：client-side parse Markdown `## ` section headers，依選擇的 Tab 只渲染對應 section
- [x] 13.6.5 `app/report/page.tsx` — 文章呈現改為卡片風格（對齊首頁 PostCard 視覺），含 source badge、points、中文摘要、連結
- [x] 13.6.6 `app/report/page.tsx` — Empty state：無報告時顯示說明文字與「重新生成」按鈕

### 13.7 Frontend — 共用元件（選用）

- [x] 13.7.1 `components/ReportCard.tsx`（可選）— 卡片樣式直接在 page 內透過 ReactMarkdown + prose 實作，差異不大，不需獨立元件

---

## 14. Daily Auto-Run + Recent Posts Filter

> Spec: `specs/ai-summarizer/spec.md` (Requirement: Daily auto-run digest with recent-posts filter)
>
> **目標**：解決兩個實際使用問題：
> 1. 報告只有在手動觸發時才生成 → 改為每日自動 + 啟動補跑
> 2. 舊文章（如 2007 年 HN 文章）混入報告 → 改為只取近期發布的文章

### 14.1 Config

- [x] 14.1.1 `config.py` — 新增 `digest_lookback_hours: int = 48`
- [x] 14.1.2 `.env` — 新增 `DIGEST_LOOKBACK_HOURS=48`

### 14.2 NewsStore

- [x] 14.2.1 `news_store.py` — `get_unsent_relevant_posts(limit, since=None)` 加入 `since: datetime | None` 參數，當有值時加 `WHERE posted_at >= since` 條件

### 14.3 DigestNotifier

- [x] 14.3.1 `digest_notifier.py` — `__init__` 加入 `lookback_hours: int = 48`
- [x] 14.3.2 `digest_notifier.py` — `generate_digest()` 計算 `since = now - timedelta(hours=lookback_hours)` 並傳入 store
- [x] 14.3.3 `digest.py` (API route) — 傳入 `lookback_hours=settings.digest_lookback_hours`
- [x] 14.3.4 `scheduler.py` — 傳入 `lookback_hours=settings.digest_lookback_hours`

### 14.4 Startup Catch-up

- [x] 14.4.1 `main.py` (lifespan) — 啟動時檢查過去 23 小時內是否有 report；若無，在背景執行一次 digest
- [x] 14.4.2 Catch-up 使用獨立 DB session，避免阻塞啟動流程（用 `threading.Thread`）

### 14.5 Tests

- [x] 14.5.1 `test_news_store.py` — `get_unsent_relevant_posts` 含 `since` 參數：舊文章被過濾
- [x] 14.5.2 `test_digest_notifier.py` — `generate_digest()` lookback_hours=48 排除舊文章
- [x] 14.5.3 `test_digest_notifier.py` — `lookback_hours=0` 時不篩選（向下相容）

### 14.6 End-to-End Validation

- [x] 14.6.1 重啟 backend，啟動時自動補跑報告（id=5，2026-04-04T00:01:31，post_count=20）
- [x] 14.6.2 確認 48h 內有 107 筆相關文章，舊文章不再混入
- [x] 14.6.3 `http://localhost:3000/report` 日期 Pill 新增今日報告

---

## 15. LLM / Agent 整合

> Spec: `specs/llm-agent-integration/spec.md`

### Phase 15a：每日技術簡報（自動化）✅ 完成 2026-04-05

- [x] 15a.1 `app/briefing/briefing_generator.py` — BriefingGenerator class：呼叫 Groq，輸出繁體中文開發者簡報
- [x] 15a.2 `DigestNotifier.__init__` 加入 `briefings_output_dir` 參數
- [x] 15a.3 `DigestNotifier.run()` — 摘要報告生成後自動呼叫 `_run_briefing()`
- [x] 15a.4 `config.py` — 新增 `briefings_output_dir: str = "briefings"`
- [x] 15a.5 `scheduler.py` / `digest.py` / `main.py` — 傳入 `briefings_output_dir`
- [x] 15a.6 `scripts/generate_briefing.py` — 手動執行版本，呼叫 `/api/summary/latest` → Groq → `briefings/YYYY-MM-DD.md`
- [x] 15a.7 `.gitignore` — 加入 `briefings/`

### Phase 15b：MCP Server（Claude Code / Desktop 整合）✅ 完成 2026-04-05

- [x] 15b.1 `pyproject.toml` — 新增 `mcp>=1.0.0` 依賴
- [x] 15b.2 `backend/mcp_server.py` — FastMCP server，直連 SQLite
- [x] 15b.3 `search_ai_news(query, days=0, limit=10)` — 關鍵字搜尋，`days=0` 不限時間
- [x] 15b.4 `get_daily_report(date="today")` — 取指定日期報告
- [x] 15b.5 `get_posts_by_category(category, days=7, limit=10)` — 依分類篩選
- [x] 15b.6 `os.chdir(_BACKEND_DIR)` — 修正 SQLite 相對路徑問題
- [x] 15b.7 Claude Code 整合驗證：`claude mcp list` 顯示 `✓ Connected`

### Phase 15c：`add_article` MCP tool — 知識庫自我擴充 🚧 待實作

> **目的**：LLM 在論壇/外部搜尋到 DB 中沒有的技術文章時，可直接寫入知識庫。
> 加入的文章設 `digest_sent=True` 跳過每日 digest，但 `search_ai_news` 可搜尋。

#### 15c.1 DB Schema — Migration 005

- [ ] 15c.1.1 `models.py` — `Post.url` 欄位加 `index=True`（加速 URL 查詢）
- [ ] 15c.1.2 `alembic/versions/005_url_index.py` — `batch_alter_table` 加 url index

#### 15c.2 NewsStore

- [ ] 15c.2.1 `news_store.py` — 新增 `get_post_by_url(url: str) -> Post | None`
- [ ] 15c.2.2 `tests/test_news_store.py` — 新增 `test_get_post_by_url_found` / `test_get_post_by_url_not_found`

#### 15c.3 MCP tool

- [ ] 15c.3.1 `mcp_server.py` — 新增 `add_article(url, content, labels, title="", posted_at="", score=7.0)`
  - 先呼叫 `get_post_by_url(url)` — 若已存在回傳「已存在」
  - `source="llm-research"`, `external_id=url`
  - `digest_sent=True`, `is_relevant=True`
  - 若 `GROQ_API_KEY` 存在，呼叫 Groq 生成 `summary_zh`
  - 呼叫 `store.commit()`
  - 回傳 Markdown 確認訊息（含生成的中文摘要）
- [ ] 15c.3.2 `posted_at` 解析：接受 `YYYY-MM-DD` 格式，空值預設今天

#### 15c.4 E2E 驗證

- [ ] 15c.4.1 透過 Claude Code 呼叫 `add_article(url=<Reddit URL>, ...)` 確認寫入
- [ ] 15c.4.2 呼叫 `search_ai_news("NotebookLM")` 確認新文章可被搜尋
- [ ] 15c.4.3 確認重複加入同 URL 時回傳「已存在」而不重複寫入
- [ ] 15c.4.4 確認加入文章**不出現**在每日 digest（`digest_sent=True`）

---

## 目前狀態 (2026-04-05)

**Phase 1–15b 全部完成。Phase 15c 待實作。**

| 項目 | 說明 |
|------|------|
| 10.4 | ✅ 完成 2026-03-31：source badge / filter / auto-refresh 手動驗證通過 |
| 10.5 | ✅ 完成 2026-03-31：本地 capture server 確認 payload 包含 `source` 欄位 |
| 11.x | ✅ 完成 2026-04-02：HN dual links + community vote count 全部實作並通過測試 |
| 12.x | ✅ 完成 2026-04-03：AI Summarizer（Groq 優先 / Gemini fallback）整合進 DigestNotifier，122 tests pass，86% coverage |
| 13.x | ✅ 完成 2026-04-03：Report history browser — 日期 Pill + 分類 Tabs，`GET /api/summary/reports` + `GET /api/summary/reports/{id}` |
| 14.x | ✅ 完成 2026-04-04：Daily auto-run + 48h lookback filter — 125 tests pass，86% coverage |
| 15a | ✅ 完成 2026-04-05：BriefingGenerator 自動整合進 DigestNotifier，手動腳本 `generate_briefing.py` |
| 15b | ✅ 完成 2026-04-05：MCP Server 含 3 個工具，已接入 Claude Code（`✓ Connected`） |
| 15c | 🚧 規劃中：`add_article` MCP tool（知識庫自我擴充）|

### 重要的已知修復（非 task 清單內）

1. **`FetchPipeline.run()` 現在呼叫 `store.commit()`** — 修復了 production scheduler 下資料不持久的 bug（session 從未 commit）
2. **`DigestNotifier.run()` 現在呼叫 `store.commit()`** — 修復了 report/summary_zh 從不持久化的 bug
3. **`digest.py` API route 補上 `gemini_api_key` / `groq_api_key` 參數** — 修復了透過 API 觸發 digest 時摘要功能未啟用的 bug
4. **Alembic migration 002 使用 `recreate="always"`** — 修復 SQLite 無名 UNIQUE constraint 導致 `alembic upgrade` 失敗的問題
5. **`test_rate_limit_integration.py` 已重寫** — 原本測試已刪除的 `XDataFetcher`；現在測試 `MultiSourceFetcher` + `GitHubFetcher` + `RedditFetcher` 的 rate limit 行為
6. **Jest config 修復** — `setupFilesAfterFramework` typo → `setupFilesAfterEnv`；移除 msw `setupServer` 改用 `jest.mock("@/lib/api")`
7. **Report category tab bug** — 分類 Tab 改用文字 `includes()` 比對取代 emoji 字串 key，修復切換 Tab 永遠顯示 AI Agent 的問題

### 刪除的檔案

| 檔案 | 原因 |
|------|------|
| `backend/app/fetcher/x_data_fetcher.py` | 已被 MultiSourceFetcher 取代 |
| `backend/tests/test_x_data_fetcher.py` | 對應測試一併刪除 |
| `dashboard/src/__tests__/mocks/handlers.ts` | msw HttpHandler 無法在 jsdom 環境初始化 |
| `dashboard/src/__tests__/mocks/server.ts` | 同上 |

### 新增的檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/fetcher/source_post.py` | `SourcePost` dataclass |
| `backend/app/fetcher/hn_fetcher.py` | HackerNewsFetcher |
| `backend/app/fetcher/reddit_fetcher.py` | RedditFetcher |
| `backend/app/fetcher/github_fetcher.py` | GitHubFetcher |
| `backend/app/fetcher/multi_source_fetcher.py` | MultiSourceFetcher |
| `backend/alembic/versions/002_multi_source.py` | Schema migration |
| `backend/tests/test_hn_fetcher.py` | 6 tests |
| `backend/tests/test_reddit_fetcher.py` | 7 tests |
| `backend/tests/test_github_fetcher.py` | 7 tests |
| `dashboard/jest.polyfill.js` | Node.js 18+ fetch globals polyfill for jsdom |
| `dashboard/src/__tests__/mocks/mock-data.ts` | `mockPost` fixture (msw-free) |
