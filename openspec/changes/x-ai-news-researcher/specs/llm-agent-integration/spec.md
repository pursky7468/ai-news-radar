# LLM / Agent 整合規格

> 討論日期：2026-04-04
> 狀態：規劃中，尚未實作

---

## 背景

現有系統已能每日自動抓取 HN / Reddit / GitHub 的 AI 新聞、進行相關性評分、以 Groq LLaMA 生成繁體中文摘要，並在 `/report` 頁面顯示歷史彙整報告。

本規格記錄將此系統作為 LLM / Agent 資料來源的設計方向與實作計畫。

---

## 使用情境

### 情境 1：開發輔助（按需查詢）

**場景：** 開發新功能時，需要讓 Agent 搜尋最新技術方案。

**範例：**
```
使用者：我要實作 streaming LLM responses，有什麼現成方案？
Claude：[呼叫 search_ai_news("streaming LLM")]
      → 取回 5 篇相關近期文章
      → 整合進技術建議回答
```

**需求：**
- Agent 能按需查詢，不需一次載入所有資料
- 支援關鍵字搜尋（現有）→ 未來支援語意搜尋
- 接入 Claude Desktop / Claude agent 生態

**最適方案：MCP Server（Phase 15）**

---

### 情境 2：每日技術簡報（定期彙整）

**場景：** 每天早上自動生成一份 Markdown 簡報，由 LLM 分析今日 AI 新聞並提供趨勢洞察與開發建議。

**流程：**
```
今日 report（已有）→ Groq 分析 → briefings/YYYY-MM-DD.md
```

**輸出格式（範例）：**
```markdown
# AI 技術簡報 — 2026-04-04

## 今日重點趨勢
1. **Multi-agent 框架成熟化** — AutoGen、KaibanJS 進入穩定版...
2. **本地 LLM 推論加速** — llama.cpp 新版效能提升 30%...

## 開發者值得關注
- KaibanJS：JavaScript 原生 agent 框架，適合前端工程師...

## 本週行動建議
1. 試試 Ollama 最新版本，本地跑 LLaMA 3 速度顯著改善
2. 關注 MCP 協議社群生態，與 Claude 整合越來越成熟
```

**需求：**
- 以現有 `GET /api/summary/latest` 取得今日報告
- 送至 Groq 加上分析 prompt（趨勢識別、開發者洞察、行動建議）
- 儲存為 `briefings/YYYY-MM-DD.md`（不入 Git）
- 可手動執行，未來整合進每日排程
- Email 交付**暫緩**，先產出本地 Markdown 檔案

**最適方案：Briefing Script（Phase 15a，優先）**

---

## 架構決策

| 方向 | 說明 | Token 效益 | 優先級 |
|------|------|-----------|--------|
| **Compact Context Endpoint** | `GET /api/context` 回傳純 Markdown，無冗餘 JSON 欄位 | 省 70–80% | P1 |
| **Briefing Script** | 每日 Groq 分析 → `briefings/YYYY-MM-DD.md` | 高價值輸出 | P0（最先做） |
| **MCP Server** | 包裝現有 API 為 MCP tools，接入 Claude Desktop | 按需取用 | P1 |
| **語意搜尋** | 向量搜尋，讓查詢更精準 | 精準省 token | P2（未來） |

### 現在已可用（無需開發）

- `GET /api/summary/latest` → 取回 Markdown 報告 → 手動貼給 Claude 分析
- `GET /api/summary/reports` → 歷史報告列表
- `/report` 頁面 → 人工瀏覽

---

## 實作計畫

### Phase 15a：每日技術簡報 Script（情境 2）

**檔案：** `backend/scripts/generate_briefing.py`

**步驟：**
1. 呼叫本地 API 取得最新報告內容
2. 組合分析 prompt（繁體中文、趨勢 + 洞察 + 建議）
3. 送至 Groq LLaMA 3.3 生成簡報
4. 儲存至 `briefings/YYYY-MM-DD.md`

**Prompt 結構：**
```
你是一位資深 AI 工程師的技術助理。
以下是今日 AI 新聞彙整，請生成一份開發者技術簡報，包含：
1. 3–5 個今日重點技術趨勢（各 2–3 句說明）
2. 對軟體開發者最值得關注的技術或工具
3. 1–2 個具體行動建議

格式：繁體中文 Markdown，不超過 600 字。

今日新聞彙整：
{report_content}
```

**輸出位置：** `briefings/YYYY-MM-DD.md`（加入 `.gitignore`）

---

### Phase 15b：MCP Server（情境 1）

**工具設計：**

```python
search_ai_news(query: str, days: int = 7, limit: int = 5)
# → 回傳符合 query 的近期文章（精簡 Markdown）

get_daily_report(date: str = "today")
# → 回傳指定日期彙整報告

get_posts_by_category(category: str, days: int = 7)
# → 回傳指定分類（ai-agent / ai-model / ai-tool）最新文章
```

**接入方式：** Claude Desktop MCP 設定

---

### Phase 16：語意搜尋（未來）

- 文章內容做 embedding（Groq embedding API 或本地模型）
- SQLite `sqlite-vec` 或 pgvector
- 新增 `GET /api/search?q=xxx&semantic=true`
- 提升情境 1 的查詢精準度

---

## 目前狀態

| 情境 | 現況 |
|------|------|
| 情境 2（簡報）| 報告已自動生成，Script 尚未實作 |
| 情境 1（開發輔助）| 需等 MCP Server 完成 |
| Email 交付 | 暫緩 |
