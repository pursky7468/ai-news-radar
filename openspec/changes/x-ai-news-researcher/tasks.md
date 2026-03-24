## 1. Project Setup & Test Infrastructure

- [x] 1.1 Initialize Python project with pyproject.toml (FastAPI, Tweepy, scikit-learn, APScheduler, SQLAlchemy, Alembic, psycopg2-binary, python-dotenv, PyYAML)
- [x] 1.2 Add test dependencies: pytest, pytest-asyncio, pytest-cov, factory-boy, httpx, respx
- [x] 1.3 Configure pytest.ini: test discovery, asyncio mode, coverage report (fail below 80%)
- [x] 1.4 Create `tests/conftest.py` with shared fixtures: in-memory SQLite engine, test NewsStore, sample post factory
- [x] 1.5 Initialize Next.js project for the dashboard (TypeScript, Tailwind CSS)
- [x] 1.6 Add frontend test dependencies: Jest, React Testing Library, msw (Mock Service Worker)
- [x] 1.7 Configure Jest with jsdom environment and RTL setup file
- [x] 1.8 Create Docker Compose file with services: api, db (PostgreSQL), and dashboard
- [x] 1.9 Create .env.example with all required environment variables (X API keys, DB URL, SMTP config, webhook URL, API key)
- [x] 1.10 Set up Alembic for database migrations

## 2. Database & News Store (TDD)

- [x] 2.1 [RED] Write failing tests for NewsStore: `test_upsert_inserts_new_post`, `test_upsert_deduplicates_by_x_post_id`, `test_query_filters_by_label`, `test_query_filters_by_min_score`, `test_query_filters_by_date_range`, `test_query_filters_by_keyword`, `test_mark_digest_sent`, `test_get_unsent_relevant_posts`, `test_update_last_fetch_at`, `test_get_last_fetch_at_returns_null_before_first_fetch`
- [x] 2.2 Create Alembic migration for `posts` table (x_post_id unique, author_handle, content, url, posted_at, fetched_at, relevance_score, is_relevant, labels jsonb, digest_sent) and `system_state` table (key varchar PK, value text, updated_at)
- [x] 2.3 [GREEN] Implement `NewsStore.upsert_post` — make insert and dedup tests pass
- [x] 2.4 [GREEN] Implement `NewsStore.query_posts` with label/score/date/sort params — make filter tests pass
- [x] 2.5 [GREEN] Implement `NewsStore.mark_digest_sent` and `get_unsent_relevant_posts` — make digest tests pass
- [x] 2.6 [GREEN] Implement `NewsStore.get_post_by_id` — make lookup tests pass
- [x] 2.7a [GREEN] Implement `NewsStore.update_last_fetch_at` and `get_last_fetch_at` — used by FetchPipeline and health endpoint
- [x] 2.7 Add indexes on `posted_at`, `relevance_score`, and `is_relevant` columns
- [x] 2.8 [REFACTOR] Consolidate query builder logic; confirm all tests still pass

## 3. Relevance Scorer (TDD)

- [x] 3.1 [RED] Write failing tests: `test_high_weight_terms_score_high`, `test_generic_terms_score_moderate`, `test_no_match_scores_zero`, `test_label_agent_assigned`, `test_label_multi_group`, `test_label_other_fallback`, `test_config_loads_from_yaml`, `test_config_falls_back_to_defaults`, `test_cache_hit_skips_scoring`, `test_cache_miss_triggers_scoring`, `test_is_relevant_true_at_threshold`, `test_is_relevant_false_below_threshold`
- [x] 3.2 [GREEN] Implement `RelevanceScorer` class with built-in tiered keyword weight dictionary
- [x] 3.3 [GREEN] Implement `score_post`: sum matched term weights, normalize to 0–10, clamp — make score tests pass
- [x] 3.4 [GREEN] Implement label assignment from keyword group matches — make label tests pass
- [x] 3.5 [GREEN] Implement YAML/JSON config loader with fallback to defaults — make config tests pass
- [x] 3.6 [GREEN] Implement cache check against NewsStore — make cache tests pass
- [x] 3.7 [GREEN] Implement `is_relevant` flag from configurable threshold — make threshold tests pass
- [x] 3.8 [REFACTOR] Extract weight normalization into a pure helper; verify coverage >= 90%

## 4. X Data Fetcher (TDD)

- [x] 4.1 [RED] Write failing tests with mocked Tweepy: `test_fetch_by_keywords_returns_posts`, `test_fetch_by_keywords_empty_results`, `test_fetch_from_account_returns_posts`, `test_fetch_skips_unknown_account`, `test_rate_limit_waits_and_retries`, `test_rate_limit_skips_after_max_retries`, `test_dedup_excludes_existing_post_ids`, `test_dedup_includes_new_post_ids`, `test_pagination_follows_next_token`, `test_pagination_stops_at_limit`
- [x] 4.2 [GREEN] Implement `XDataFetcher` class with Bearer Token auth via Tweepy Client
- [x] 4.3 [GREEN] Implement `fetch_by_keywords`: build query string, call recent search, follow `next_token` pagination until limit — make keyword and pagination tests pass
- [x] 4.4 [GREEN] Implement `fetch_from_accounts`: resolve handle to user ID, call timeline, follow `next_token` pagination until limit — make account and pagination tests pass
- [x] 4.5 [GREEN] Implement rate limit handling: read `x-rate-limit-reset` header, sleep until reset, retry up to 3× — make rate limit tests pass
- [x] 4.6 [GREEN] Implement deduplication check against NewsStore — make dedup tests pass
- [x] 4.7 Load keyword list and account list from environment/config file
- [x] 4.8 [REFACTOR] Unify response parsing; confirm all mocked tests pass

## 5. Digest Notifier (TDD)

- [x] 5.1 [RED] Write failing tests: `test_generate_digest_returns_top_n_unsent`, `test_generate_digest_empty_when_no_posts`, `test_send_email_marks_posts_sent_on_success`, `test_send_email_does_not_mark_sent_on_failure`, `test_send_webhook_posts_json_payload`, `test_send_webhook_skipped_when_not_configured`, `test_run_returns_correct_summary`, `test_run_does_not_mark_sent_when_any_channel_fails`
- [x] 5.2 [GREEN] Implement `DigestNotifier.generate_digest`: query NewsStore for top N unsent relevant posts — make digest tests pass
- [x] 5.3 [GREEN] Implement `send_email`: format HTML email, send via SMTP, mark posts sent on success — make email tests pass
- [x] 5.4 [GREEN] Implement `send_webhook`: POST JSON to configured URL, mark posts sent on success — make webhook tests pass
- [x] 5.5 [GREEN] Implement `run`: orchestrate both channels, skip unconfigured ones, return summary — make run tests pass
- [x] 5.6 [REFACTOR] Extract HTML email template; confirm all delivery tests still pass

## 6. REST API (TDD)

- [x] 6.1 Define Pydantic schemas: `Post`, `PaginatedNewsResponse`, `DigestTriggerResult`, `HealthResponse`
- [x] 6.2 [RED] Write failing API tests using FastAPI TestClient: `test_health_ok`, `test_health_db_down_returns_503`, `test_health_returns_last_fetch_at`, `test_news_list_default`, `test_news_list_filter_by_label`, `test_news_list_filter_by_min_score`, `test_news_list_filter_by_keyword`, `test_news_list_pagination`, `test_news_get_by_id_found`, `test_news_get_by_id_not_found`, `test_digest_trigger_sends`, `test_digest_trigger_no_posts`, `test_auth_missing_key_returns_401`, `test_auth_invalid_key_returns_401`
- [x] 6.3 [GREEN] Implement API key authentication middleware — make auth tests pass
- [x] 6.4 [GREEN] Implement `GET /api/health` — make health tests pass
- [x] 6.5 [GREEN] Implement `GET /api/news` with all filter/sort/pagination params — make list tests pass
- [x] 6.6 [GREEN] Implement `GET /api/news/{id}` — make lookup and 404 tests pass
- [x] 6.7 [GREEN] Implement `POST /api/digest/trigger` — make trigger tests pass
- [x] 6.8 [REFACTOR] Consolidate query param validation into shared dependency; confirm all API tests pass

## 7. Scheduler & Pipeline (TDD)

- [x] 7.1 [RED] Write failing tests: `test_pipeline_runs_fetch_then_score_then_store`, `test_pipeline_logs_counts`, `test_pipeline_handles_empty_fetch`, `test_scheduler_registers_two_jobs`
- [x] 7.2 [GREEN] Implement `FetchPipeline`: orchestrate fetch → score → upsert → update_last_fetch_at in sequence — make pipeline tests pass
- [x] 7.3 [GREEN] Add structured logging per pipeline stage (fetch count, score count, store count, errors)
- [x] 7.4 [GREEN] Configure APScheduler with fetch job (every 15 min) and digest job (configurable cron) — make scheduler tests pass
- [x] 7.5 Wire scheduler start/stop to FastAPI lifespan event
- [x] 7.6 [REFACTOR] Ensure pipeline steps are independently testable without scheduler running

## 8. Dashboard (TDD — Next.js)

- [x] 8.1 Create API client module with `X-API-Key` header injection; set up msw handlers for all API routes
- [x] 8.2 [RED] Write failing tests for `NewsFeed`: renders post cards, shows score badge, shows labels, renders X link, triggers load-more on scroll
- [x] 8.3 [GREEN] Implement `NewsFeed` component — make feed render tests pass
- [x] 8.4 [RED] Write failing tests for `FilterBar`: label chips toggle filter, score slider updates query, clear resets state
- [x] 8.5 [GREEN] Implement `FilterBar` component — make filter tests pass
- [x] 8.6 [RED] Write failing tests for `SearchBox`: filters visible posts by keyword, shows empty state on no match
- [x] 8.7 [GREEN] Implement `SearchBox` component — make search tests pass
- [x] 8.8 [RED] Write failing tests for `DigestButton`: shows success toast on trigger, shows error toast on failure
- [x] 8.9 [GREEN] Implement `DigestButton` component — make digest tests pass
- [x] 8.10 [RED] Write failing test for auto-refresh: new-posts banner appears when poll returns new items
- [x] 8.11 [GREEN] Implement auto-refresh (5-minute polling) and new-posts banner — make auto-refresh test pass
- [x] 8.12 Add loading skeletons and empty states for all data-fetching components
- [x] 8.13 [REFACTOR] Extract shared post card sub-component; confirm all component tests pass

## 9. Configuration & Deployment

- [x] 9.1 Write `config.py` that loads all env vars with defaults and validates required ones on startup
- [x] 9.2 Write Dockerfile for the FastAPI backend (multi-stage, production-ready)
- [x] 9.3 Write Dockerfile for the Next.js dashboard (multi-stage)
- [x] 9.4 Update Docker Compose with volume for PostgreSQL data persistence and health checks
- [x] 9.5 Write `scripts/seed_keywords.py` to populate the default keyword and account watchlist
- [x] 9.6 Document setup steps in README.md (env vars, first run, API key generation, running tests)

## 10. End-to-End Validation

- [x] 10.1 Run full test suite (`pytest --cov` backend, `jest --coverage` frontend); confirm all tests pass and coverage >= 80% — backend: 60/60 passed, 91% coverage
- [ ] 10.2 Run full pipeline manually against live X API: fetch real posts, score with TF-IDF scorer, verify DB entries and score distribution
- [ ] 10.3 Test API endpoints via curl or Postman: list, filter by label, trigger digest
- [ ] 10.4 Verify dashboard loads feed, filters work, and digest button sends notification
- [ ] 10.5 Confirm digest email/webhook received with correct post data
- [x] 10.6 Verify rate limit handling by simulating 429 responses in integration test — 8 integration tests added (tests/test_rate_limit_integration.py), 68/68 passed
