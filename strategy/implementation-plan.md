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

**狀態**：⬜ 待執行
**目標**：修復亂碼問題、重設 briefing 結構、修正 highlight score ArXiv 偏權

#### Checklist

**語言驗證（`backend/app/briefing/briefing_generator.py`）**
- [ ] 新增 `_validate_language(text: str) -> bool` 函式，使用 Unicode block 判斷
  - 允許：CJK（U+4E00–U+9FFF）、Basic Latin（U+0000–U+007F）、CJK 標點
  - 觸發：其他 block（越南文等拉丁擴充、阿拉伯文、泰文等）
- [ ] `_call_groq()` 後執行語言驗證
  - 觸發 → 用強化 prompt 重試一次
  - 重試仍失敗 → 在輸出頂部加 `⚠️ [語言品質警告]`，寫入 warning log
- [ ] 新增對應單元測試（`backend/tests/test_briefing_generator.py`）

**Briefing 結構（`backend/app/briefing/briefing_generator.py`）**
- [ ] 修改 `_BRIEFING_PROMPT`：
  - 新增 4 個維度的分區指示（技術模式與架構、實踐技巧與工具用法、開源動態）
  - 加入「說明為什麼值得注意」的指示，不只轉述標題
  - 要求：某維度無內容時不顯示該區塊
- [ ] `BriefingGenerator.generate()` 加 source filter：組裝 `report_content` 前排除 `source == 'arxiv'` 的文章

**Highlight Score（`backend/app/briefing/highlight_scorer.py`）**
- [ ] 修改 `source_weight` 映射，移除 `arxiv`：
  ```python
  SOURCE_WEIGHTS = {"github": 3, "hackernews": 2, "reddit": 1}
  # arxiv 移除，每日 highlight 只在非 arxiv 文章中計算
  ```
- [ ] 新增對應單元測試

**Commit message**：`feat: fix briefing quality — language validation, 4-dimension structure, highlight score`

---

### Phase 3：v2 Bug 修復

**狀態**：⬜ 待執行
**目標**：修復 digest 超時、重複發 email、crash loop 三個既有 bug

#### Checklist

**Digest 非同步（`backend/app/api/routes/digest.py`）**
- [ ] `POST /api/digest/trigger` 改為非同步：
  - 立即回傳 `202 Accepted` + `{"job_id": "<uuid>", "status": "queued"}`
  - 實際 digest 在 background task 執行
- [ ] 新增 `GET /api/digest/jobs/{job_id}` 查詢狀態（可選：簡單用 in-memory dict 記錄）
- [ ] 更新對應測試

**Email 各 channel 獨立 flag**
- [ ] 新增 Alembic migration 008：
  - `posts` 表新增 `email_sent BOOLEAN DEFAULT FALSE`
  - `posts` 表新增 `webhook_sent BOOLEAN DEFAULT FALSE`
  - 將現有 `digest_sent=True` 的資料遷移：`email_sent=True, webhook_sent=True`
  - 保留 `digest_sent` 欄位（向後相容），但標記為 deprecated
- [ ] `backend/app/notifier/digest_notifier.py`：
  - email 成功 → 只標記 `email_sent=True`
  - webhook 成功 → 只標記 `webhook_sent=True`
  - 查詢未發送的 posts 時，依各自 flag 獨立過濾
- [ ] 更新對應測試

**Crash Loop Cooldown（`backend/app/pipeline/scheduler.py`）**
- [ ] 啟動時 digest trigger 邏輯加 30 分鐘 cooldown：
  - 讀取 `system_state` 的 `last_digest_at`（需新增此欄位或用現有 key-value 表）
  - 若距離上次 digest < 30 分鐘，跳過啟動觸發
- [ ] 更新對應測試

**Commit message**：`fix: digest async 202, per-channel sent flags (migration 008), crash loop cooldown`

---

### Phase 4：關鍵字擴充與新 Reddit 來源

**狀態**：⬜ 待執行
**目標**：讓 briefing 開始捕捉「AI 協作技巧」維度的內容

#### Checklist

**keywords.yaml**
- [ ] 新增 `ai_collaboration_techniques` 群組（high_weight + standard_weight）
  ```yaml
  ai_collaboration_techniques:
    high_weight:
      - graph memory
      - memory graph
      - agent memory
      - claude.md
      - CLAUDE.md
      - system prompt pattern
      - agentic workflow
      - multi-agent context
      - context window management
      - tool use pattern
      - knowledge graph agent
      - long-term memory LLM
      - agent orchestration
    standard_weight:
      - prompt engineering
      - vibe coding
      - AI workflow
      - MCP server
  ```
- [ ] 確認新群組的 label 映射（建議：`ai-technique`）
- [ ] 在 `relevance_scorer.py` 的 `_GROUP_LABEL_MAP` 新增對應映射

**新增 Reddit Subreddits（`config.py` 或 `.env`）**
- [ ] `reddit_subreddits` 預設值加入 `ClaudeAI,PromptEngineering`
- [ ] 確認新 subreddits 的 fetch 不超過 Reddit API rate limit
- [ ] 更新 `README.md` 的環境變數說明表格

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

### Phase 6：Hybrid Search + Embedding Pipeline

**狀態**：⬜ 待執行（等 Phase 5 完成）
**目標**：MCP `search_ai_news` 升級為 Hybrid Search，提升 Claude Code 查詢相關性

#### Checklist

**Embedding Pipeline**
- [ ] 新增 Alembic migration 009：`posts` 表新增 `embedding BLOB` 欄位
- [ ] 實作 `EmbeddingService`：
  - 使用 `sentence-transformers/all-MiniLM-L6-v2`
  - Server 啟動時執行 warmup（預載模型）
  - `embed(text: str) -> list[float]`
  - Fallback：HF Inference API（依 env var 切換）
- [ ] 新增非同步 embedding worker（`run_in_executor` 包裝 CPU-bound 呼叫）：
  - 文章入庫後 enqueue embedding job
  - 計算完成後更新 `posts.embedding`
- [ ] 歷史資料補算 script（`backend/scripts/backfill_embeddings.py`）

**向量儲存**
- [ ] SQLite：整合 `sqlite-vec`
- [ ] PostgreSQL：整合 `pgvector`（依 `DATABASE_URL` 自動選擇）

**Hybrid Search**
- [ ] 實作 `HybridSearchService`：
  - FTS5 搜尋（top-20）→ 結果集 A
  - 向量搜尋（top-20，cosine similarity）→ 結果集 B
  - RRF 合併（k=60）→ 最終 top-N
- [ ] `search_ai_news` MCP tool 升級為 Hybrid Search（介面不變）

**新增 MCP Tools**
- [ ] `list_techniques()` → 回傳 `keywords.yaml` 中的群組名稱列表
- [ ] `get_posts_by_technique(technique, days, limit)` → 查詢符合群組的文章

**Commit message**：`feat: hybrid search (FTS5 + embedding + RRF), list_techniques MCP tool`

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
| 1 | 文件修正 | ⬜ 待執行 | — | — |
| 2 | Briefing 品質修復 | ⬜ 待執行 | — | — |
| 3 | v2 Bug 修復 | ⬜ 待執行 | — | — |
| 4 | 關鍵字擴充與新 Reddit 來源 | ⬜ 待執行 | — | — |
| 觀察期 | 評估 threshold 與 Group 2 優先序 | ⬜ 待執行 | — | — |
| 5 | RSS Fetcher | ⬜ 待執行 | — | — |
| 6 | Hybrid Search + Embedding | ⬜ 待執行 | — | — |
| 7 | 設定檔框架完善 | ⬜ 待執行 | — | — |
