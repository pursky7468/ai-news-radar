# AI News Researcher

Automated multi-source AI news pipeline that continuously fetches, scores, and surfaces AI-related posts from **Hacker News**, **Reddit**, and **GitHub** — no paid API credentials required.

## Architecture

- **Backend**: FastAPI + APScheduler (Python 3.11)
- **Sources**: Hacker News (Algolia API), Reddit (public JSON), GitHub (REST API)
- **Scoring**: TF-IDF + keyword weight model (no external API)
- **Storage**: PostgreSQL (production) / SQLite (dev)
- **Dashboard**: Next.js 14 (TypeScript + Tailwind CSS)
- **Delivery**: Email (SMTP) + webhook digest

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

預期結果：84 tests passed，coverage ≥ 80%

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
| `REDDIT_SUBREDDITS` | 否 | 監控的 subreddits，逗號分隔（預設：`MachineLearning,LocalLLaMA,...`） |
| `REDDIT_KEYWORDS` | 否 | Reddit 全站搜尋關鍵字（選填） |
| `REDDIT_FETCH_LIMIT` | 否 | Reddit 每次 fetch 最多幾筆（預設 100） |
| `GITHUB_MONITORED_REPOS` | 否 | 監控 release 的 repo，逗號分隔（`owner/repo` 格式） |
| `GITHUB_KEYWORDS` | 否 | GitHub repo 搜尋關鍵字（預設：`ai agent,llm,rag`） |
| `GITHUB_FETCH_LIMIT` | 否 | GitHub 每次 fetch 最多幾筆（預設 30） |
| `GITHUB_TOKEN` | 否 | GitHub Personal Access Token（提升 Search API rate limit 到 30 rpm） |
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
| POST | `/api/digest/trigger` | 手動觸發 digest |

所有 `/api/news*` 和 `/api/digest*` 需帶 `X-API-Key: <your_api_key>` header。

### 支援的查詢參數 (`GET /api/news`)

| 參數 | 型別 | 說明 |
|------|------|------|
| `source` | string | 篩選來源：`hackernews` / `reddit` / `github` |
| `since` | ISO 8601 | 只回傳 `posted_at > since` 的 posts（用於 auto-refresh） |
| `label` | string | 篩選 label（`ai-agent` / `ai-tool` / `ai-model` / `other`） |
| `min_score` | float | 最低相關性分數 |
| `q` | string | 關鍵字搜尋（全文） |
| `sort` | string | 排序：`date_desc`（預設）/ `score_desc` |
| `page` | int | 頁碼（預設 1） |
| `per_page` | int | 每頁筆數（預設 20，最大 100） |

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
→ 設定 `GITHUB_TOKEN` 環境變數（GitHub Personal Access Token），可將 Search API rate limit 從 10 rpm 提升到 30 rpm

**Q: Reddit API 回傳 403**
→ Reddit 公開 API 需要自訂 User-Agent。系統已自動設定，若仍出現問題請確認網路環境沒有封鎖 reddit.com
