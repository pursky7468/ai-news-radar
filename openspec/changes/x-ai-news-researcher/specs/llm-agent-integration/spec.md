# LLM / Agent 整合規格

> 討論日期：2026-04-04
> 更新日期：2026-04-05
> 狀態：Phase 15a ✅ 完成 / Phase 15b ✅ 完成 / Phase 15c 規劃中

---

## 背景

現有系統已能每日自動抓取 HN / Reddit / GitHub 的 AI 新聞、進行相關性評分、以 Groq LLaMA 生成繁體中文摘要，並在 `/report` 頁面顯示歷史彙整報告。

本規格記錄將此系統作為 LLM / Agent 資料來源的設計方向與實作計畫。

---

## 核心目的（2026-04-05 釐清）

系統服務**兩種不同需求**，必須分開設計：

```
用途 A：每日 Digest（時效性）
  → 只需要「最近 48h 的新文章」
  → digest_sent=False + posted_at >= now-48h

用途 B：知識庫搜尋（完整性）
  → 需要「DB 裡所有文章，不限時間」
  → search_ai_news 不加時間限制
```

LLM 手動加入的文章屬於**用途 B**，不進入每日 digest。

---

## 使用情境

### 情境 1：開發輔助 — LLM 搜尋知識庫（已完成 Phase 15b）

**場景：** 開發新功能時，讓 Agent 搜尋 DB 中所有相關技術（不限時間）。

**流程：**
```
使用者：我要實作 streaming LLM responses，有什麼現成方案？
Claude：[呼叫 search_ai_news("streaming LLM", days=0)]
      → 取回 DB 中所有相關文章（不限年份）
      → 整合進技術建議回答
```

**已實作工具（`backend/mcp_server.py`）：**
```python
search_ai_news(query: str, days: int = 0, limit: int = 10)
# days=0 = 不限時間，搜尋全部 DB

get_daily_report(date: str = "today")
# 取得指定日期彙整報告

get_posts_by_category(category: str, days: int = 7, limit: int = 10)
# 依分類篩選：ai-agent / ai-model / ai-tool / other
```

---

### 情境 1b：知識庫自我擴充 — LLM 發現新技術後寫入 DB（Phase 15c）

**場景：** LLM 搜尋時發現 DB 中沒有某篇相關文章，主動將其存入，讓知識庫持續成長。

**流程：**
```
Claude：[呼叫 search_ai_news("NotebookLM MCP")]
      → DB 沒有相關結果
      → 自行到 Reddit/GitHub 搜尋
      → 找到 https://reddit.com/r/MachineLearning/comments/...
      → [呼叫 add_article(url=..., content=..., labels=["ai-tool"])]
      → 文章存入 DB，下次搜尋就能找到
```

**設計決策：**

| 欄位 | 值 | 說明 |
|------|-----|------|
| `source` | `"llm-research"` | 區分自動爬蟲 vs LLM 手動加入 |
| `external_id` | `url` | URL 作為唯一識別 |
| `posted_at` | 文章原始發佈日（LLM 判斷）或今天 | 保留語意正確性 |
| `digest_sent` | `True` | 歷史文章跳過每日 digest |
| `is_relevant` | `True` | LLM 已判斷相關性 |
| `summary_zh` | Groq 自動生成 | 加入時同步產生中文摘要 |

**URL 去重策略：**
- 加入前先查詢 `url` 是否已存在（不限 source）
- 若存在回傳「已存在」訊息，不重複寫入
- 避免 LLM 爬蟲與 HN/Reddit 自動爬蟲出現重複記錄

---

### 情境 2：每日技術簡報（已完成 Phase 15a）

**場景：** 每天早上自動生成一份 Markdown 簡報，由 Groq 分析今日 AI 新聞並提供趨勢洞察與開發建議。

**已實作：**
- `backend/app/briefing/briefing_generator.py` — BriefingGenerator class
- 整合進 `DigestNotifier.run()`，每日 digest 後自動執行
- 輸出至 `briefings/YYYY-MM-DD.md`（不入 Git）
- 可手動執行：`python scripts/generate_briefing.py`

**輸出格式（範例）：**
```markdown
# AI 技術簡報 — 2026-04-05

## 今日重點趨勢
1. **Multi-agent 框架成熟化** — AutoGen、KaibanJS 進入穩定版...
2. **本地 LLM 推論加速** — llama.cpp 新版效能提升 30%...

## 開發者值得關注
- KaibanJS：JavaScript 原生 agent 框架，適合前端工程師...

## 本週行動建議
1. 試試 Ollama 最新版本，本地跑 LLaMA 3 速度顯著改善
2. 關注 MCP 協議社群生態，與 Claude 整合越來越成熟
```

---

## 架構決策

| 方向 | 說明 | 狀態 |
|------|------|------|
| **Briefing Script** | 每日 Groq 分析 → `briefings/YYYY-MM-DD.md` | ✅ Phase 15a 完成 |
| **MCP Server** | 包裝現有 API 為 MCP tools，接入 Claude Code/Desktop | ✅ Phase 15b 完成 |
| **add_article MCP tool** | LLM 發現新技術 → 寫入知識庫 | 🚧 Phase 15c 規劃中 |
| **語意搜尋** | 向量搜尋，讓查詢更精準 | Phase 16（未來） |

### 兩種文章的生命週期對比

```
自動爬蟲文章                    LLM 手動加入文章
─────────────────               ─────────────────────────
source: hackernews/reddit       source: llm-research
digest_sent: False              digest_sent: True（跳過 digest）
posted_at: 原始發佈日           posted_at: 原始發佈日（LLM 判斷）
↓                               ↓
進入每日 digest                 直接進知識庫
↓                               ↓
search_ai_news 可搜尋           search_ai_news 可搜尋 ✅
```

---

## 實作計畫

### Phase 15a：每日技術簡報 ✅ 完成

- `backend/app/briefing/briefing_generator.py`
- `backend/scripts/generate_briefing.py`
- 整合進 `DigestNotifier.run()`
- `briefings/` 加入 `.gitignore`

### Phase 15b：MCP Server ✅ 完成

- `backend/mcp_server.py`
- 工具：`search_ai_news`、`get_daily_report`、`get_posts_by_category`
- 直連 SQLite（無 HTTP 依賴）
- `os.chdir(backend_dir)` 確保相對 DB 路徑正確

### Phase 15c：`add_article` MCP tool 🚧

**新增工具：**
```python
add_article(
    url: str,           # 文章 URL（必填，用於去重）
    content: str,       # 文章內容摘要（必填）
    labels: list[str],  # ["ai-agent", "ai-model", "ai-tool", "other"]
    title: str = "",    # 文章標題（選填）
    posted_at: str = "", # 原始發佈日 YYYY-MM-DD（選填，預設今天）
    score: float = 7.0, # 相關性分數（選填，預設 7.0）
)
```

**需改動的元件：**

| 元件 | 改動 |
|------|------|
| `news_store.py` | 新增 `get_post_by_url(url) -> Post \| None` |
| `mcp_server.py` | 新增 `add_article` tool |
| `models.py` | 在 `url` 欄位加 index（加速 URL 查詢） |
| `alembic` | Migration 005：url index |

**不需改動：**
- Digest / lookback 邏輯（`digest_sent=True` 已隔離）
- Dashboard / report 頁面
- `search_ai_news` tool（已支援全時間搜尋）

### Phase 16：MCP 工具擴充（v2 Phase B）🚧 待實作

> 任務清單：`tasks.md` § 18.3
> Spec：`specs/weekly-briefing/spec.md`

**新增工具（不修改現有三個工具）**：

```python
get_trending_tools(days: int = 7, limit: int = 10) -> list[dict]
# 回傳近 N 天熱度上升的工具清單
# 資料結構：[{"tool": "LangChain", "count": 12, "sample_url": "..."}]

get_weekly_summary(week_offset: int = 0) -> str
# 回傳週報 Markdown 內容
# week_offset=0 本週，-1 上週
```

**搜尋工具擴充（向下相容）**：

```python
# 現有簽名（繼續有效）
search_ai_news(query: str, days: int = 0, limit: int = 10)

# 擴充後（新參數全部 optional，現有呼叫無需修改）
search_ai_news(
    query: str,
    days: int = 0,
    limit: int = 10,
    date_from: str = None,   # YYYY-MM-DD，可選
    date_to: str = None,     # YYYY-MM-DD，可選
)
```

### Phase 17：語意搜尋（未來）

- 文章內容做 embedding（Groq embedding API 或本地模型）
- SQLite `sqlite-vec` 或 pgvector
- 新增 `GET /api/search?q=xxx&semantic=true`
- 提升情境 1 的查詢精準度

---

## 目前 MCP Tools 清單

| Tool | 簽名 | 狀態 |
|------|------|------|
| `search_ai_news` | `(query, days=0, limit=10)` | ✅ Phase 15b 完成 |
| `get_daily_report` | `(date="today")` | ✅ Phase 15b 完成 |
| `get_posts_by_category` | `(category, days=7, limit=10)` | ✅ Phase 15b 完成 |
| `add_article` | `(url, content, labels, title, posted_at, score)` | 🚧 Phase 15c 待實作 |
| `search_ai_news` (擴充) | `+date_from, +date_to` | 🚧 v2 Phase A 待實作 |
| `get_trending_tools` | `(days=7, limit=10)` | 🚧 v2 Phase B 待實作 |
| `get_weekly_summary` | `(week_offset=0)` | 🚧 v2 Phase B 待實作 |

## 目前狀態

| 情境 | 現況 |
|------|------|
| 情境 2（每日簡報）| ✅ 完成：自動生成 `briefings/YYYY-MM-DD.md` |
| 情境 1（MCP 搜尋）| ✅ 完成：3 個工具已接入 Claude Code |
| 情境 1b（知識庫擴充）| 🚧 Phase 15c 待實作 |
| 跨日期搜尋 | 🚧 v2 Phase A 待實作 |
| 週報 / 趨勢摘要 | 🚧 v2 Phase B 待實作 |
| 熱門工具查詢 | 🚧 v2 Phase B 待實作 |
| Email 交付 | 暫緩 |
