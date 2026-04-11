# AI News Radar v3 — Product Spec

**版本**: 1.1
**日期**: 2026-04-12
**狀態**: 已確認，進入實作計劃階段

---

## 變更記錄

| 版本 | 日期 | 變更說明 |
|------|------|---------|
| 1.0 | 2026-04-11 | 初版，PM × 架構師需求確認 |
| 1.1 | 2026-04-12 | 四人跨部門審查後更新：修正成功指標、補充語言驗證規則、確認 ArXiv source filter 實作方式、補充 Embedding 非同步設計、新增 list_techniques MCP tool、澄清雙重權重系統、新增架構決策 |

---

## 1. 背景與問題陳述

### 1.1 現況

AI News Radar 可以每日從 HN、Reddit、GitHub、ArXiv 抓取 AI 相關資訊，並生成繁體中文每日 briefing（`.md` 檔案）和 web dashboard。

**已確認的現況數據（2026-04-12 查驗）**：
- 評分系統：純關鍵字權重計分（非 TF-IDF，詳見 § 8）
- 當前 relevance threshold：5.0（`config.py:40`）
- FTS5：運作中，使用 workaround 映射（詳見 § 8）
- Embedding：尚未實作

### 1.2 核心問題

用戶每天都會閱讀 briefing，但沒有「這個有用」的印象。問題分為兩個層面：

**內容策展失準**
現有關鍵字針對「AI 產業新聞」，沒有涵蓋用戶真正想看的「AI 協作技巧與實踐模式」。

**呈現品質不穩定**
LLM 生成繁體中文時偶發語言混雜（已確認：`2026-04-10.md` 第 5 點出現越南文 `một`）。Briefing 結構沒有反映不同內容類型的閱讀價值。

### 1.3 為什麼是重大改版

同時涉及：資料來源策略、關鍵字體系、LLM prompt 架構、briefing 格式設計、ArXiv 呈現定位、v2 bug 修復。

---

## 2. 用戶與使用情境

### 2.1 主要用戶

- **當前**：開發者本人（單一用戶）
- **目標**：開源社群可 fork 並自行配置，追蹤自己關心的技術領域

### 2.2 使用情境

| 情境 | 描述 |
|------|------|
| 每日閱讀 | 每天開啟 `.md` briefing，掃描當日重點，遇到感興趣的內容點連結看原文 |
| 深度瀏覽 | 開啟 web dashboard，捲動瀏覽完整列表，點連結到原始文章 |
| 開發輔助 | Claude Code 透過 MCP Server 在實作過程中查詢是否有新技術或方案可參考 |

### 2.3 MCP Server 的實際角色

MCP 是 **Claude Code 在開發過程中的技術情報查詢介面**，不是用戶手動查詢工具。優化重點是查詢結果的技術相關性，不是易用性。

---

## 3. 目標與成功指標

### 3.1 目標

1. 用戶讀完每日 briefing 後，至少有一則內容讓他想點進去看原文
2. Briefing 輸出無語言混雜或亂碼
3. 開源社群可以透過修改設定檔（不改程式碼）來客製化追蹤的技術領域

### 3.2 成功指標（可自動量測）

| 指標 | 標準 | 量測方式 |
|------|------|---------|
| 內容品質 | 每日 briefing 中 `relevance_score ≥ 7` 的文章佔比 ≥ 40% | 每次生成 briefing 後自動計算並記錄 |
| 維度覆蓋 | 每日至少有 1 篇來自「技術模式」或「實踐技巧」維度的文章 | 依 keywords 群組分類後計算 |
| 語言品質 | 連續 30 天無語言混雜警告事件 | 語言驗證 log |
| 可客製化 | Fork 後只需修改 `config/` 下的設定檔，不需改任何 Python 程式碼 | 文件驗證 |

> **Threshold 決策**：當前 threshold 維持 5.0，等 Group 1 所有改動完成後，觀察上述指標，再決定是否調整至 7.0。

---

## 4. 功能範圍

### 4.1 內容策展重設計

#### 設計方向

將內容分為四個維度，每個維度有獨立的關鍵字群組：

| 維度 | 說明 | 主要來源 |
|------|------|---------|
| 技術模式與架構 | 新的 AI 系統設計方式，例如 graph memory、multi-agent 架構 | HN、Reddit、RSS |
| 實踐技巧與工具用法 | 具體使用方式，例如 claude.md 寫法、prompt pattern | Reddit（r/ClaudeAI、r/PromptEngineering）、HN |
| 研究前沿 | ArXiv 論文（每週彙整，不每日推送） | ArXiv |
| 開源動態 | 值得關注的新 repo、版本發布 | GitHub |

#### 關鍵字體系擴充

在現有 `keywords.yaml` 新增 `ai_collaboration_techniques` 群組：

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

#### 新增資料來源（Group 1：Reddit；Group 2：RSS）

**Group 1（立即新增）**
| 來源 | 類型 | 維度 |
|------|------|------|
| r/ClaudeAI | Reddit subreddit | 實踐技巧 |
| r/PromptEngineering | Reddit subreddit | 實踐技巧 |

**Group 2（RSS Fetcher 完成後新增）**
| 來源 | 類型 | 維度 |
|------|------|------|
| Simon Willison's Blog | RSS | 實踐技巧、技術模式 |
| Swyx (swyx.io) | RSS | 技術模式 |

> Facebook 社群無公開 API，不在可接入範圍內。

---

### 4.2 Briefing 品質與格式改版

#### 4.2.1 語言品質保證

**問題**：LLM 偶發語言混雜（已確認：`2026-04-10.md` 第 5 點出現越南文 `một`）。

**語言驗證規則（Unicode block 判斷）**：
- 允許：CJK 統一表意文字（U+4E00–U+9FFF）、基本拉丁文（U+0000–U+007F）、CJK 標點
- 觸發警告：其他 Unicode block（越南文等拉丁擴充、阿拉伯文、泰文等）

英文技術術語（`LLM`、`RAG`、`MCP`、`API`、`fine-tuning`、`embedding` 等）屬於基本拉丁文，不觸發警告。

**處理流程**：
1. LLM 生成後執行語言驗證
2. 觸發警告 → 用強化 prompt 重試一次
3. 重試仍失敗 → 保留內容，在該段落加 `⚠️ [語言品質警告]`，寫入 log

**強化 Prompt 範本**：
```
你必須只使用繁體中文（台灣用語）。
不允許出現越南文、簡體中文、日文或任何其他語言的詞彙。
英文專有名詞（如 LLM、RAG、API）可以保留。
```

#### 4.2.2 Briefing 結構重設計

**新結構**：依四個維度分區，ArXiv 文章每日排除（由 BriefingGenerator 加 source filter：`source != 'arxiv'`）。

```markdown
# AI News Radar — {date}

## 技術模式與架構
> 今日有 N 則相關內容

### {標題}
{說明為什麼這個值得注意，不只是轉述標題}
[原文連結]({url}) · {來源} · {分數}

---

## 實踐技巧與工具用法
> 今日有 N 則相關內容

...

---

## 開源動態
> 今日有 N 則相關內容

...
```

**設計原則**：
- 每則摘要說明「為什麼值得注意」，不只轉述標題
- 某個維度當日無相關內容 → 該區塊不顯示
- ArXiv 文章每日排除，歸入每週彙整

#### 4.2.3 Highlight Score 修正

當前公式中 ArXiv `source_weight=4` 遠高於其他來源，但 ArXiv 已移出每日 briefing。

**修正後的每日 highlight score**：
```
highlight_score = relevance_score * 0.5
               + source_weight * 0.3   # github=3, hn=2, reddit=1（移除 arxiv）
               + recency_decay * 0.2
```

每日 highlight 僅在 `source != 'arxiv'` 的文章中計算。

---

### 4.3 ArXiv 知識庫定位

ArXiv 論文節奏太學術，不適合每日 briefing，但有長期知識庫的價值。

**實作方式**：
- `BriefingGenerator` 組每日 briefing 時加 `source != 'arxiv'` filter
- `WeeklyBriefingGenerator` 專門查 `source == 'arxiv'`，生成每週論文摘要子區塊
- Web Dashboard：利用現有 source filter（`?source=arxiv`）分離顯示，不加新 Tab 或新 route

**每週論文摘要格式**（附加在 weekly briefing 末尾）：
```markdown
## 本週 ArXiv 論文
> 收錄本週值得關注的論文（cs.AI / cs.LG / cs.CL）

- **{論文標題}** — {一句話說明核心貢獻} [原文]({url})
```

---

### 4.4 MCP Server — Hybrid Search

#### 為什麼需要 Hybrid Search

Claude Code 查詢時使用自然語言描述，FTS5 只能比對詞彙，Hybrid Search 同時跑 FTS5 和向量搜尋後合併，兼顧精確和語意。

#### 搜尋架構

```
查詢
  ├── FTS5 關鍵字搜尋（top-K）  → 結果集 A
  └── 向量相似度搜尋（top-K）   → 結果集 B
        ↓
  Reciprocal Rank Fusion（RRF，k=60）合併排名
        ↓
  最終結果（top-N）
```

**FTS5 現況說明**：migration 006 使用 workaround，`title = substr(content, 1, 100)`，`summary = summary_zh`。FTS5 是運作的，Hybrid Search 可以直接使用。

#### Embedding Pipeline

**模型**：`sentence-transformers/all-MiniLM-L6-v2`（22MB，CPU 執行）

**執行方式（非同步，不阻塞 fetch pipeline）**：
```
fetch pipeline → 文章入庫（DB insert）
                      ↓
              非同步 embedding queue
              （FastAPI + run_in_executor，
                避免 CPU-bound 任務 block event loop）
                      ↓
              計算完成後更新 DB embedding 欄位
```

**Cold start 處理**：server 啟動時預先執行模型 warmup（下載並載入模型），第一次 embed 時不觸發額外延遲。

**Fallback**：若本地 CPU 負擔有感，可切換為 HF Inference API（免費，1,000 req/day）。

> **排除 Gemini Embedding API**：專案中 Gemini API 有穩定性問題（已有 circuit breaker 為證），embedding pipeline 需要可靠執行。

#### 向量儲存

| 環境 | 方案 |
|------|------|
| SQLite（開發） | `sqlite-vec` |
| PostgreSQL（生產） | `pgvector` |

依 `DATABASE_URL` 自動選擇。

#### MCP Tools（新增 / 升級）

| Tool | 說明 |
|------|------|
| `search_ai_news`（升級） | 升級為 Hybrid Search，介面不變（向後相容） |
| `get_posts_by_technique`（新增） | 依技術類型查詢，taxonomy 從 `keywords.yaml` 群組名稱派生 |
| `list_techniques`（新增） | 回傳目前可用的 technique 列表，供 Claude Code 在呼叫 `get_posts_by_technique` 前枚舉 |

`list_techniques` 的必要性：Claude Code 無法事先知道有效的 technique 值，必須有枚舉介面。

---

### 4.5 開源客製化框架

#### 設定檔架構（目標狀態）

```
config/
  keywords.yaml   # 關鍵字體系（現有，擴充）
  sources.yaml    # 資料來源列表（新增，type discriminator 模式）
  briefing.yaml   # Briefing 格式與語言設定（新增）
  scoring.yaml    # 維度呈現優先序（新增）
```

#### 兩套設定的作用邊界（不交叉）

| 設定檔 | 作用層級 | 說明 |
|--------|---------|------|
| `keywords.yaml` | 詞彙層級 | 決定單篇文章的相關性分數（現有邏輯不變） |
| `scoring.yaml` | 維度層級 | 決定各維度在 briefing 中的呈現優先序（新增） |

兩者不疊加，不交叉。修改 `scoring.yaml` 不影響文章的 `relevance_score`。

#### sources.yaml 格式（type discriminator）

```yaml
sources:
  - id: hackernews
    type: api
    provider: hackernews
    dimension: tech_patterns
    enabled: true

  - id: reddit_claude
    type: reddit
    subreddit: ClaudeAI
    fetch_limit: 50
    dimension: technique_tips
    enabled: true

  - id: simon_willison    # Group 2
    type: rss
    url: https://simonwillison.net/atom/everything/
    dimension: technique_tips
    poll_interval_minutes: 120   # RSS 不需要 15 分鐘 poll 一次
    enabled: false
```

---

## 5. 非功能性需求

| 需求 | 說明 |
|------|------|
| 語言一致性 | Briefing 輸出必須是純繁體中文（英文術語除外），無其他語言混雜 |
| 配置優先 | 所有可客製化的行為必須外露為設定檔，不寫死在程式碼中 |
| 設計意圖可見 | 每個主要設計決策都應有說明（why，不只是 what） |
| 向後相容 | 現有的 `.env` 環境變數和 Alembic migration 繼續有效 |
| 非同步優先 | CPU-bound 任務（embedding）和長時間 I/O（digest trigger）不阻塞主 event loop |

---

## 6. Out of Scope

| 項目 | 原因 |
|------|------|
| SaaS / Hosted 版本 | 目標是開源練習，不是商業產品 |
| Mobile App | 不符合現有使用情境 |
| Multi-user 支援 | 單用戶設計，開源 fork 各自部署 |
| Facebook 社群內容 | 無公開 API，技術上不可行 |
| Twitter/X 整合 | API 費用過高，不符合開源免費原則 |
| Web Dashboard 語意搜尋 | 用戶捲動瀏覽，不依賴搜尋介面 |
| Threshold 調整（v3 範圍內） | 等 Group 1 完成後觀察再決定，不在實作計劃中 |

---

## 7. 待驗證假設

| 假設 | 風險程度 | 驗證方式 |
|------|---------|---------|
| **核心假設**：用戶「沒有特別印象」的原因是內容策展失準，而非其他因素（習慣、時間、格式） | 高 | Group 1 完成後觀察 2 週，看成功指標是否改善 |
| 用戶會因為「技術模式」類內容而點進原文 | 中 | 觀察 2 週的閱讀行為 |
| 個人部落格 RSS 有足夠的更新頻率 | 中 | 試接 RSS 後確認（Group 2 前） |
| 每週論文摘要比每日推送更符合閱讀節奏 | 低 | 改版後使用觀察 |

---

## 8. 架構決策記錄

| 決策 | 結論 | 理由 |
|------|------|------|
| `sources.yaml` 格式 | Type discriminator（`type: rss/reddit/api`） | 三種來源類型各自有必要欄位，discriminator 讓設定對開源用戶可讀可擴充 |
| 語言驗證失敗處理 | 重試一次 → 若仍失敗標記 `⚠️` + log | 靜默丟棄最不透明；重試先嘗試自動修復；標記保留讓用戶知道問題 |
| 語言驗證規則 | Unicode block 判斷（允許 CJK + Basic Latin） | 白名單難以窮舉；block 判斷覆蓋所有非預期語言 |
| ArXiv 呈現位置 | 現有 source filter 分離，不加 Tab / route | 用戶捲動瀏覽，額外導覽層增加不必要摩擦 |
| ArXiv 每日排除方式 | `BriefingGenerator` 加 `source != 'arxiv'` filter | 最小改動，不影響抓取 pipeline；ArXiv 資料仍入庫可查詢 |
| `get_posts_by_technique` taxonomy | 從 `keywords.yaml` 群組名稱派生 + `list_techniques()` 枚舉 | 避免雙重維護；AI caller 需要枚舉介面才能正確使用 |
| Embedding 模型 | `all-MiniLM-L6-v2`（本地 CPU），Fallback: HF Inference API | Gemini API 不穩定；本地模型零外部依賴，CPU 負擔極低 |
| Embedding 執行方式 | 非同步 background worker（`run_in_executor`） | CPU-bound 任務不能在 async context 直接執行，會 block event loop |
| `scoring.yaml` 與 `keywords.yaml` | 明確分層，不交叉 | 兩套系統作用在不同層，交叉會導致分數計算邏輯混亂 |
| **評分系統實際實作** | 純關鍵字權重計分（非 TF-IDF） | `relevance_scorer.py` 確認：無 IDF 計算，為 `Σ(命中詞 × 權重) + 社群加分`，截斷至 10。所有 spec 中的「TF-IDF」描述均為不準確，應更正為「keyword weight scoring」 |
| **FTS5 實作方式** | Workaround：`title = substr(content, 1, 100)`，`summary = summary_zh` | DB schema 無獨立 `title` 欄位，開發者用有意識的 workaround 完成實作。FTS5 運作正常，spec 描述不準確但實作無誤 |
| **Highlight score（每日）** | 移除 arxiv source_weight | ArXiv 已移出每日 briefing，保留 arxiv 高權重會導致精選邏輯矛盾 |
| Digest trigger 非同步 | 202 Accepted + job_id | 同步執行 20 篇 × 4 秒 = 80 秒，超過 HTTP timeout；火-即-忘模式對 curl 和 APScheduler 都適用 |
| Email channel 獨立 flag | `email_sent` + `webhook_sent` 各自獨立 | 全有或全無的 mark-sent 導致 Email 重複發送；各自獨立才能正確重試失敗的 channel |
| Crash loop 防護 | startup cooldown 30 分鐘 | 服務重啟不應重複觸發 LLM API，耗盡免費 quota |

---

*版本 1.1 — 四人審查後確認，可進入實作計劃。*
