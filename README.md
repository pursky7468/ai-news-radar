# AI News Radar

> Self-hosted multi-source AI news aggregator with MCP server — build your personal AI knowledge base and query it directly in Claude.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Tests](https://img.shields.io/badge/tests-180%20passed-brightgreen.svg)
![MCP](https://img.shields.io/badge/MCP-server%20included-purple.svg)

---

## Why This Project?

Most AI news tools are **one-time searches** — they query the web, return results, and forget everything. AI News Radar is different:

- **Persistent knowledge base** — continuously fetches and stores AI news from 4 sources, building a searchable local database that grows over time
- **Zero paid APIs for core functionality** — HN, Reddit, GitHub, and ArXiv are all free
- **MCP Server included** — Claude can query your personal AI news database directly in conversation, without switching tools
- **Daily Chinese briefing** — auto-generated Traditional Chinese (zh-TW) daily digest via Groq/Gemini (optional, API key required)

---

## Architecture

- **Backend**: FastAPI + APScheduler (Python 3.11)
- **Sources**: Hacker News (Algolia API), Reddit (public JSON), GitHub (REST API), ArXiv (Atom API)
- **Scoring**: Keyword weight scoring + semantic embedding (no external API required)
- **Storage**: PostgreSQL (production) / SQLite (dev)
- **Dashboard**: Next.js 14 (TypeScript + Tailwind CSS)
- **MCP Server**: 7 tools for direct Claude integration
- **Delivery**: Email (SMTP) + webhook digest (per-channel tracking)

---

## MCP Server — Claude Integration

AI News Radar ships with a built-in MCP Server. Once configured, Claude can query your local AI news database directly in conversation.

### Available MCP Tools

| Tool | Signature | Description |
|------|-----------|-------------|
| `search_ai_news` | `(query, days=0, limit=10)` | Hybrid search (FTS5 + semantic vector) across all stored articles |
| `get_daily_report` | `(date="today")` | Retrieve the daily briefing for a given date |
| `get_posts_by_category` | `(category, days=7, limit=10)` | Fetch posts by category (ai-agent, ai-tool, ai-model) |
| `get_trending_tools` | `(days=7, limit=10)` | Top trending AI tools by mention count |
| `get_weekly_summary` | `(week_offset=0)` | Weekly trend summary (0=this week, -1=last week) |
| `list_techniques` | `()` | List all technique groups defined in keywords.yaml |
| `get_posts_by_technique` | `(technique, days=7, limit=10)` | Semantic search by technique group (e.g. ai_collaboration_techniques) |

### Setup

**Step 1 — Start the backend**
```bash
cd backend
uvicorn app.main:app --port 8000
```

**Step 2 — Configure Claude Code**

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project-level):
```json
{
  "mcpServers": {
    "ai-news": {
      "command": "python",
      "args": ["/absolute/path/to/backend/mcp_server.py"],
      "env": {
        "DATABASE_URL": "sqlite:////absolute/path/to/backend/dev.db",
        "API_KEY": "changeme"
      }
    }
  }
}
```

**Step 3 — Use in Claude**
```
# Examples
What AI agent tools trended this week?
Search my news database for "RAG pipeline" from the last 7 days.
Show me today's AI briefing.
```

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Docker + Docker Compose | any | `docker --version` (Option A only) |

---

## Option A — Docker Compose (推薦，最快)

適合：想快速跑起整個系統，不想手動安裝依賴。

### 1. 設定環境變數

```bash
cp .env.example .env
```

最少要填的欄位：

```env
API_KEY=changeme                          # 自訂一組 API 金鑰
DATABASE_URL=postgresql://postgres:postgres@db:5432/newsresearcher
```

> 產生安全隨機金鑰：`python -c "import secrets; print(secrets.token_urlsafe(32))"`
>
> GitHub token（選填）：設定 `GITHUB_TOKEN` 可將 Search API rate limit 從 10 rpm 提升到 30 rpm。

### 2. 啟動所有服務

```bash
docker compose up --build
```

| 服務 | URL |
|------|-----|
| Backend API | http://localhost:8000 |
| API 文件 (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |

### 3. 確認正常運行

```bash
# Health check
curl http://localhost:8000/api/health

# 列出 posts（第一次 fetch 約 15 分鐘後才有資料）
curl -H "X-API-Key: changeme" http://localhost:8000/api/news

# 依來源篩選
curl -H "X-API-Key: changeme" "http://localhost:8000/api/news?source=hackernews"
curl -H "X-API-Key: changeme" "http://localhost:8000/api/news?source=reddit"
curl -H "X-API-Key: changeme" "http://localhost:8000/api/news?source=github"

# 手動觸發 digest
curl -X POST -H "X-API-Key: changeme" http://localhost:8000/api/digest/trigger
```

---

## Option B — Local Dev（不需要 Docker）

適合：開發、debug、跑測試。使用 SQLite，不需要安裝 PostgreSQL。

### 步驟 1 — Backend 設定

```bash
cd backend

# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 安裝依賴（含測試工具）
pip install -e ".[test]"
```

### 步驟 2 — Backend 環境變數

在 `backend/` 目錄下建立 `.env` 檔案：

```bash
# backend/.env
DATABASE_URL=sqlite:///./dev.db
API_KEY=changeme
# GitHub token 選填（提高 rate limit）
GITHUB_TOKEN=
```

### 步驟 3 — 建立資料庫 schema

```bash
# 在 backend/ 目錄下執行
alembic upgrade head
```

### 步驟 4 — 啟動 Backend

```bash
uvicorn app.main:app --reload --port 8000
```

確認：http://localhost:8000/api/health 回傳 `{"status":"ok"}`

### 步驟 5 — 載入測試資料（選擇性，方便 UI 開發）

```bash
python -c "
import sqlite3, json
from datetime import datetime, timedelta
conn = sqlite3.connect('dev.db')
sources = ['hackernews', 'reddit', 'github']
for i in range(6):
    src = sources[i % 3]
    conn.execute(
        'INSERT OR IGNORE INTO posts (source, external_id, author_handle, content, url, posted_at, fetched_at, relevance_score, is_relevant, labels, digest_sent) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (src, f'seed_{i}', f'researcher_{i}',
         f'AI agent uses tool calling and multi-agent orchestration #{i}',
         f'https://example.com/{src}/seed_{i}',
         (datetime(2026,3,1) + timedelta(days=i)).isoformat(),
         datetime.now().isoformat(),
         round(8.5 - i * 0.5, 1), 1, json.dumps(['ai-agent']), 0)
    )
conn.commit(); conn.close()
print('Seeded 6 posts across 3 sources')
"
```

### 步驟 6 — Frontend 設定

```bash
cd ../dashboard

# 安裝依賴
npm install

# 建立環境變數檔（必要）
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=changeme
EOF
```

> **重要**：`.env.local` 必須在啟動 Next.js **之前**建立，否則需要重啟 dev server。

### 步驟 7 — 啟動 Dashboard

```bash
npm run dev
```

Dashboard: http://localhost:3000

---

## 跑測試

### Backend 單元測試

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pytest
```

預期結果：220 tests passed，coverage ≥ 80%

### Frontend 單元測試

```bash
cd dashboard
npm test
```

預期結果：17 tests passed，coverage ≥ 80%

### E2E 測試（Playwright）

**前置條件**：Backend (port 8000) 和 Dashboard (port 3000 或 3001) 都必須在跑。

```bash
# 確認兩個服務都起來了
curl http://localhost:8000/api/health
curl http://localhost:3000

# 跑 E2E
npx playwright test e2e/dashboard.spec.js --reporter=line
```

---

## 環境變數說明

| 變數 | 必填 | 說明 |
|------|------|------|
| `DATABASE_URL` | 是 | PostgreSQL: `postgresql://user:pass@host/db` / SQLite: `sqlite:///./dev.db` |
| `API_KEY` | 是 | Dashboard → Backend 的 API 金鑰（自訂） |
| `HN_KEYWORDS` | 否 | Hacker News 搜尋關鍵字，逗號分隔（預設：`ai agent,LLM,RAG,MCP,...`） |
| `HN_FETCH_LIMIT` | 否 | HN 每次 fetch 最多幾筆（預設 100） |
| `REDDIT_SUBREDDITS` | 否 | 監控的 subreddits，逗號分隔（預設：`MachineLearning,LocalLLaMA,singularity,artificial,ClaudeAI,PromptEngineering`） |
| `REDDIT_KEYWORDS` | 否 | Reddit 全站搜尋關鍵字（選填） |
| `REDDIT_FETCH_LIMIT` | 否 | Reddit 每次 fetch 最多幾筆（預設 100） |
| `GITHUB_MONITORED_REPOS` | 否 | 監控 release 的 repo，逗號分隔（`owner/repo` 格式） |
| `GITHUB_KEYWORDS` | 否 | GitHub repo 搜尋關鍵字（預設：`ai agent,llm,rag`） |
| `GITHUB_FETCH_LIMIT` | 否 | GitHub 每次 fetch 最多幾筆（預設 30） |
| `GITHUB_TOKEN` | 否 | GitHub Personal Access Token（提升 Search API rate limit 到 30 rpm） |
| `ARXIV_CATEGORIES` | 否 | ArXiv 分類，逗號分隔（預設：`cs.AI,cs.LG,cs.CL`） |
| `ARXIV_MAX_RESULTS` | 否 | ArXiv 每次 fetch 最多幾筆（預設 50） |
| `SMTP_HOST` | 否 | Email digest 用 SMTP 主機 |
| `SMTP_PORT` | 否 | SMTP port（預設 587） |
| `SMTP_USER` | 否 | SMTP 帳號 |
| `SMTP_PASSWORD` | 否 | SMTP 密碼 |
| `DIGEST_EMAIL_FROM` | 否 | Digest 寄件人 |
| `DIGEST_EMAIL_TO` | 否 | Digest 收件人 |
| `DIGEST_WEBHOOK_URL` | 否 | Slack / Discord / 自訂 webhook URL |
| `FETCH_INTERVAL_MINUTES` | 否 | 自動 fetch 間隔（預設 15） |
| `DIGEST_CRON` | 否 | Digest 排程 cron（預設 `0 8 * * *`） |
| `RELEVANCE_THRESHOLD` | 否 | 相關性最低分數（預設 5） |
| `GEMINI_API_KEY` | 否 | Google Gemini API Key（中文日報，選填） |
| `GROQ_API_KEY` | 否 | Groq API Key（優先於 Gemini，選填） |
| `USER_CONTEXT` | 否 | 個人化 context，注入至 briefing 提示詞（例：`I am building a RAG pipeline`） |
| `FEATURE_FTS_SEARCH` | 否 | 啟用 SQLite FTS5 全文搜尋（預設 false） |
| `FEATURE_HIGHLIGHT_SCORER` | 否 | briefing 頂部顯示 Top 3 精選（預設 false） |
| `FEATURE_WEEKLY_BRIEFING` | 否 | 每週一自動生成週報（預設 false） |
| `FEATURE_BOOKMARKS` | 否 | 啟用書籤 API（預設 false） |
| `FEATURE_ARXIV_FETCHER` | 否 | 啟用 ArXiv 論文 fetcher（預設 false） |
| `FEATURE_EMBEDDINGS` | 否 | 啟用語意 embedding + Hybrid Search（預設 false，需安裝 sentence-transformers） |
| `EMBEDDING_MODEL` | 否 | Embedding 模型名稱（預設 `sentence-transformers/all-MiniLM-L6-v2`） |
| `HF_API_TOKEN` | 否 | HuggingFace API Token，設定後改用 HF Inference API 而非本機推理 |

---

## Keyword 調整

編輯 `backend/keywords.yaml` 修改關鍵字權重，無需改程式碼。重啟 backend 後生效。

---

## API 端點速覽

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/health` | 健康檢查（無需 API Key） |
| GET | `/api/news` | 列出 posts（支援 label/score/keyword/source/since 過濾） |
| GET | `/api/news/{id}` | 取得單筆 post |
| POST | `/api/digest/trigger` | 非同步觸發 digest（回傳 202 + job_id） |
| GET | `/api/digest/jobs/{job_id}` | 查詢 digest 執行狀態 |
| GET | `/api/bookmarks` | 列出收藏 |
| POST | `/api/bookmarks` | 新增收藏 |
| DELETE | `/api/bookmarks/{id}` | 刪除收藏 |

所有 `/api/news*`、`/api/digest*`、`/api/bookmarks*` 需帶 `X-API-Key: <your_api_key>` header。

完整文件：http://localhost:8000/docs

---

## 常見問題

**Q: 啟動 backend 報錯 `no such table: posts`**
→ 跑 `alembic upgrade head`

**Q: Dashboard 顯示 "No posts found" 但 API 有資料**
→ 確認 `dashboard/.env.local` 存在且 `NEXT_PUBLIC_API_URL` 指向正確 port，然後重啟 `npm run dev`

**Q: E2E 測試 `article` elements not found**
→ 確認 backend 有資料（先執行 seed 步驟），且 `.env.local` 的 API URL 正確

**Q: GitHub API 回傳 403 / rate limit 超過**
→ 設定 `GITHUB_TOKEN` 環境變數，可將 Search API rate limit 從 10 rpm 提升到 30 rpm

**Q: Reddit API 回傳 403**
→ Reddit 公開 API 需要自訂 User-Agent。系統已自動設定，若仍出現問題請確認網路環境沒有封鎖 reddit.com

---

## Roadmap

### v1 — Implemented ✅
- Multi-source fetching (HN, Reddit, GitHub)
- Keyword weight scoring + relevance classification
- Daily Traditional Chinese briefing (Groq/Gemini)
- REST API + Next.js dashboard
- MCP Server (3 tools)

### v2 — In Progress 🚧
- [x] ArXiv as 4th data source (cs.AI, cs.LG, cs.CL)
- [x] SQLite FTS5 full-text search with date range filtering
- [x] Weekly briefing + trend summary
- [x] Top 3 algorithmic daily highlight
- [x] Expanded MCP tools (`get_trending_tools`, `get_weekly_summary`)
- [x] Article bookmarks + personal notes

### v3 — Planned 📋
- Semantic search (embedding-based)
- Official changelog RSS feeds (OpenAI, Anthropic, Google)
- Trend visualization (keyword frequency over time)
- Multi-user support

---

## Contributing

Issues and PRs are welcome. Please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE)
