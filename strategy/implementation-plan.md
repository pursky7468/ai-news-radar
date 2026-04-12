# AI News Radar v3 — 實作計劃書

**建立日期**：2026-04-12
**依據**：`strategy/spec-v3.md` v1.1
**執行原則**：每次只做一個 Phase，完成後 commit，再更新本文件狀態

---

## 執行規則

- 每個 Phase 完成所有 checklist 項目後才能 commit
- Commit 後在本文件將該 Phase 標記為 ✅ 並記錄日期
- 下一個 Phase 開始前確認上一個 Phase 的 commit 是乾淨的
- Threshold 不在任何 Phase 內，等 Group 1 全部完成後另行評估

---

## Group 1：直接改善每日 Briefing 體驗

---

### Phase 1：文件修正（無程式碼變更）

**狀態**：✅ 完成
**完成日期**：2026-04-12
**Commit**：`docs: align spec with actual implementation (scoring, FTS5, x-data-fetcher freeze)`

#### Checklist

- [x] `openspec/changes/x-ai-news-researcher/specs/x-data-fetcher/spec.md`
  - 頂部加凍結標記，說明原因（X API $100+/月，design.md 明確列為 Non-Goal）
- [x] `openspec/changes/x-ai-news-researcher/specs/relevance-scorer/spec.md`
  - 移除「TF-IDF」描述，改為「keyword weight scoring」
  - 補充實際評分公式：`score = min(10, Σ(命中詞 × 權重) + min(社群票數/100, 3))`
  - 說明正規化方式：截斷至 10，不是線性縮放
- [x] `openspec/changes/x-ai-news-researcher/specs/full-text-search/spec.md`
  - 補充說明 FTS5 workaround：`title = substr(content, 1, 100)`，`summary = summary_zh`
  - 標注這是有意為之的設計，而非 bug
- [x] `openspec/changes/x-ai-news-researcher/design.md`
  - 在 Decision § 2（Relevance Scoring）補充：實作為 keyword weight scoring，未實作 IDF 部分
- [x] `strategy/product-review-2026-04-11.md`
  - 頂部加備注：「本文為初期探索討論，最終方向以 strategy/spec-v3.md 為準」

---

### Phase 2：Briefing 品質修復

**狀態**：✅ 完成
**完成日期**：2026-04-12
**Commit**：`feat: fix briefing quality — language validation, 4-dimension structure, highlight score`
**目標**：修復亂碼問題、重設 briefing 結構、修正 highlight score ArXiv 偏權

#### Checklist

**語言驗證（`backend/app/briefing/briefing_generator.py`）**
- [x] 新增 `_validate_language(text: str) -> bool` 函式，使用 Unicode block 判斷
  - 允許：CJK（U+4E00–U+9FFF）、Basic Latin（U+0000–U+007F）、CJK 標點
  - 觸發：其他 block（越南文等拉丁擴充、阿拉伯文、泰文等）
- [x] `_call_groq()` 後執行語言驗證
  - 觸發 → 用強化 prompt 重試一次
  - 重試仍失敗 → 在輸出頂部加 `⚠️ [語言品質警告]`，寫入 warning log
- [x] 新增對應單元測試（`backend/tests/test_briefing_generator.py`）

**Briefing 結構（`backend/app/briefing/briefing_generator.py`）**
- [x] 修改 `_BRIEFING_PROMPT`：
  - 新增 4 個維度的分區指示（技術模式與架構、實踐技巧與工具用法、開源動態、產業動態）
  - 加入「說明為什麼值得注意」的指示，不只轉述標題
  - 要求：某維度無內容時不顯示該區塊
- [x] `digest_notifier._run_briefing()` 計算 highlights 前排除 `source == 'arxiv'` 的文章（prompt 說明 daily 不含 arxiv）

**Highlight Score（`backend/app/briefing/highlight_scorer.py`）**
- [x] 修改 `source_weight` 映射，移除 `arxiv`：
  ```python
  SOURCE_WEIGHTS = {"github": 3, "hackernews": 2, "reddit": 1}
  # arxiv 移除，每日 highlight 只在非 arxiv 文章中計算
  ```
- [x] 新增對應單元測試

**Commit message**：`feat: fix briefing quality — language validation, 4-dimension structure, highlight score`

---

### Phase 3：v2 Bug 修復

**狀態**：✅ 完成
**完成日期**：2026-04-12
**Commit**：`fix: digest async 202, per-channel sent flags (migration 008), crash loop cooldown`
**目標**：修復 digest 超時、重複發 email、crash loop 三個既有 bug

#### Checklist

**Digest 非同步（`backend/app/api/routes/digest.py`）**
- [x] `POST /api/digest/trigger` 改為非同步：
  - 立即回傳 `202 Accepted` + `{"job_id": "<uuid>", "status": "queued"}`
  - 實際 digest 在 background task 執行
- [x] 新增 `GET /api/digest/jobs/{job_id}` 查詢狀態（in-memory dict 記錄）
- [x] 更新對應測試

**Email 各 channel 獨立 flag**
- [x] 新增 Alembic migration 008：
  - `posts` 表新增 `email_sent BOOLEAN DEFAULT FALSE`
  - `posts` 表新增 `webhook_sent BOOLEAN DEFAULT FALSE`
  - 將現有 `digest_sent=True` 的資料遷移：`email_sent=True, webhook_sent=True`
  - 保留 `digest_sent` 欄位（向後相容），標記為 deprecated
- [x] `backend/app/notifier/digest_notifier.py`：
  - email 成功 → 只標記 `email_sent=True`
  - webhook 成功 → 只標記 `webhook_sent=True`
  - `digest_sent=True` 仍在所有 channel 成功時標記（向後相容）
- [x] 更新對應測試（含 per-channel flag 測試）

**Crash Loop Cooldown（`backend/app/pipeline/scheduler.py`）**
- [x] `_make_digest_job` 加 30 分鐘 cooldown：
  - 讀取 `system_state` 的 `last_digest_at`
  - 若距離上次 digest < 30 分鐘，跳過本次執行
  - digest 完成後更新 `last_digest_at`
- [x] `news_store.py` 新增 `get_last_digest_at()` / `set_last_digest_at()`
- [x] `test_scheduler_registers_two_jobs` 修正 API signature 不符問題
- [x] 更新對應測試

**Commit message**：`fix: digest async 202, per-channel sent flags (migration 008), crash loop cooldown`

---

### Phase 4：關鍵字擴充與新 Reddit 來源

**狀態**：✅ 完成
**完成日期**：2026-04-12
**Commit**：`feat: expand keywords with ai_collaboration_techniques, add ClaudeAI/PromptEngineering subreddits`
**目標**：讓 briefing 開始捕捉「AI 協作技巧」維度的內容

#### Checklist

**keywords.yaml**
- [x] 新增 `ai_collaboration_techniques` 群組（high_weight + standard_weight）
  - high_weight: graph memory, memory graph, agent memory, claude.md, CLAUDE.md, system prompt pattern, agentic workflow, multi-agent context, context window management, tool use pattern, knowledge graph agent, long-term memory LLM, agent orchestration
  - standard_weight: prompt engineering, vibe coding, AI workflow, MCP server
- [x] label 映射：`ai-technique`
- [x] 在 `relevance_scorer.py` 的 `_GROUP_LABEL_MAP` 新增對應映射

**新增 Reddit Subreddits（`config.py`）**
- [x] `reddit_subreddits` 預設值加入 `ClaudeAI,PromptEngineering`
- [x] 更新 `README.md` 的環境變數說明表格

**Commit message**：`feat: expand keywords with ai_collaboration_techniques, add ClaudeAI/PromptEngineering subreddits`

---

### Group 1 完成後：觀察期

**目標**：執行 2 週，收集成功指標數據，再決定以下事項：
- Threshold 是否從 5.0 調整至 7.0
- 哪些 Group 2 功能值得優先做

---

## Group 2：架構能力建設（Group 1 穩定後執行）

---

### Phase 5：RSS Fetcher

**狀態**：⬜ 待執行（等 Group 1 完成）
**目標**：新增 RSS 資料來源支援，接入 Simon Willison 和 swyx.io

#### Checklist

- [ ] 補充 RSS Fetcher spec（`openspec/changes/x-ai-news-researcher/specs/rss-fetcher/spec.md`）
  - 定義 Atom vs RSS 2.0 解析差異
  - 定義 `SourcePost` schema 映射（`title`, `content`, `url`, `posted_at`）
  - 定義 polling 頻率（獨立設定，建議預設 120 分鐘）
  - 定義 `sources.yaml` 格式範例
- [ ] 實作 `RssFetcher` class（實作 `SourceFetcher` interface）
  - 支援 Atom 和 RSS 2.0 格式
  - `poll_interval_minutes` 獨立設定（不跟 HN/Reddit 的 15 分鐘共用）
  - 加入 `sources.yaml` 設定支援
- [ ] 新增 Simon Willison、swyx.io 到 `sources.yaml`（預設 `enabled: false`）
- [ ] 單元測試（mock RSS feed response）

**Commit message**：`feat: add RSS fetcher with configurable poll interval`

---

### Phase 6：Hybrid Search + Embedding Pipeline（擴充版）

**狀態**：✅ 完成
**完成日期**：2026-04-12
**Commit**：`feat: hybrid search (FTS5 + embedding + RRF), briefing semantic augmentation, list_techniques MCP tool`
**目標**：MCP `search_ai_news` 升級為 Hybrid Search，並用語意搜尋補足 briefing 的 ai-technique 內容缺口

#### Checklist

**Embedding Pipeline**
- [x] 新增 Alembic migration 009：`posts` 表新增 `embedding BLOB` 欄位
- [x] 實作 `EmbeddingService`（`backend/app/embeddings/embedding_service.py`）：
  - 使用 `sentence-transformers/all-MiniLM-L6-v2`（本機 CPU，22MB）
  - Lazy load + warmup on scheduler start
  - `embed(text: str) -> list[float]`，`embed_text_for_post(post)`
  - Fallback：HF Inference API（`HF_API_TOKEN` env var）
  - serialize/deserialize float32 binary blob
- [x] `fetch_pipeline.py` 每次 fetch 後自動計算新文章 embedding
- [x] Backfill script（`backend/scripts/backfill_embeddings.py`）

**向量儲存**
- [x] SQLite BLOB + Python-side cosine similarity（adequate for <50k posts）
- 放棄 sqlite-vec / pgvector（安裝複雜，收益不高）

**Hybrid Search**（`backend/app/embeddings/vector_search.py`）
- [x] `vector_search()` — cosine similarity in-memory
- [x] `hybrid_search()` — FTS5 + vector + RRF (k=60)
- [x] `search_ai_news` MCP tool 升級為 Hybrid Search

**Briefing 語意擴充（擴充版新增）**
- [x] `semantic_augment_for_briefing()` — 每日 briefing 前語意搜尋 ai-technique 內容
- [x] `digest_notifier._semantic_augment()` — 注入到 digest 流程，確保 briefing 有 ai-technique 文章

**新增 MCP Tools**
- [x] `list_techniques()` — 回傳 keywords.yaml 群組列表
- [x] `get_posts_by_technique(technique, days, limit)` — 語意 + label fallback 雙模式查詢

**新增依賴**：`sentence-transformers>=3.0.0`, `numpy>=1.26.0`

---

### Phase 7：設定檔框架完善

**狀態**：⬜ 待執行（等 Phase 6 完成）
**目標**：完成開源客製化框架，讓 fork 後只需改設定檔

#### Checklist

- [ ] 建立 `config/sources.yaml`（type discriminator 格式，含完整說明）
- [ ] 建立 `config/briefing.yaml`（語言、格式偏好設定）
- [ ] 建立 `config/scoring.yaml`（維度呈現優先序，與 keywords.yaml 分層）
- [ ] 讓 backend 讀取 `config/` 目錄下的設定檔，優先於 `keywords.yaml` 預設值
- [ ] 更新 `README.md`：說明 config/ 框架和各設定檔的用途

**Commit message**：`feat: config/ framework for open-source customization`

---

## 進度追蹤

| Phase | 說明 | 狀態 | 完成日期 | Commit |
|-------|------|------|---------|--------|
| 1 | 文件修正 | ✅ 完成 | 2026-04-12 | `docs: align spec with actual implementation` |
| 2 | Briefing 品質修復 | ✅ 完成 | 2026-04-12 | `feat: fix briefing quality — language validation, 4-dimension structure, highlight score` |
| 3 | v2 Bug 修復 | ✅ 完成 | 2026-04-12 | `fix: digest async 202, per-channel sent flags (migration 008), crash loop cooldown` |
| 3 | v2 Bug 修復 | ✅ 完成 | 2026-04-12 | `fix: digest async 202, per-channel sent flags (migration 008), crash loop cooldown` |
| 4 | 關鍵字擴充與新 Reddit 來源 | ✅ 完成 | 2026-04-12 | `feat: expand keywords with ai_collaboration_techniques, add ClaudeAI/PromptEngineering subreddits` |
| 觀察期 | 評估 threshold 與 Group 2 優先序 | 🔵 進行中 | — | — |
| 5 | RSS Fetcher | ⬜ 待執行 | — | — |
| 6 | Hybrid Search + Embedding（擴充） | ✅ 完成 | 2026-04-12 | `feat: hybrid search (FTS5+embedding+RRF), briefing semantic augmentation` |
| 7 | 設定檔框架完善 | ⬜ 待執行 | — | — |
