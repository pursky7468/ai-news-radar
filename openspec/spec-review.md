# Spec 審查報告 — x-ai-news-researcher v2 + v3 strategy

> 審查人：隔壁部門 PM + 系統架構師
> 審查日期：2026-04-11
> 審查範圍：`openspec/changes/x-ai-news-researcher/specs/` 全部 spec 檔案 + `strategy/` 全部文件

---

## 一、重大矛盾（直接打臉 design.md）

### 1. x-data-fetcher spec 根本不該存在

`design.md` 明確記錄：

> "X / Twitter integration (API cost $100+/month, high noise ratio)" — **Non-Goals (v2)**

然而 `specs/x-data-fetcher/spec.md` 卻完整定義了 X API v2 的抓取規格。

這個 spec 沒有 feature flag、沒有版本標示、沒有說明何時會實作。
**問題**：開發者看到 spec 就可能動手實作，在不知情的情況下引入 $100+/月的 API 費用。
**結論**：這份 spec 應被標示為「已拒絕 / 凍結」或直接刪除。

---

## 二、架構設計問題（系統架構師觀點）

### 2. POST /api/digest/trigger 必定 HTTP timeout

**相關 spec**：`news-api/spec.md` + `ai-summarizer/spec.md`

`news-api` spec 說：
> "runs synchronously and the response includes posts_included, email_sent, webhook_sent"

`ai-summarizer` spec 說：
> "waits 4 seconds before the next post to respect free-tier rate limits (15 RPM)"
> "SUMMARY_POST_LIMIT: 20 posts"

**問題**：20 篇 × 4 秒 = **最少 80 秒**，再加 SMTP 傳送、webhook 呼叫。
HTTP 預設 timeout 通常為 30–60 秒，同步觸發必然超時。
spec 中找不到任何非同步處理、background job、或 polling 機制的設計。

**建議方向**：改為 202 Accepted + job ID，或將摘要生成移至非同步任務。

---

### 3. FTS5 索引欄位與實際 schema 不一致

**相關 spec**：`full-text-search/spec.md` + `news-store/spec.md`

`full-text-search` spec 說：
> "Search SHALL be performed via SQLite FTS5... against the `title` and `summary` columns"

`news-store` spec 定義的 schema 中，只有 `content` 欄位，**沒有** `title` 或 `summary` 欄位。
ArXiv spec 也把「title + abstract」concatenate 後存入 `content`。

**問題**：FTS5 virtual table 要索引的欄位在資料庫裡根本不存在。
migration 006 無法正確執行，或執行後索引的是錯誤欄位。

**建議**：明確決定是 (a) 拆分 `content` 為 `title` + `body`，或 (b) FTS5 索引 `content` 欄位，並更新 spec。

---

### 4. Weekly Briefing 與 Daily Report 存放位置不一致

**相關 spec**：`weekly-briefing/spec.md` + `ai-summarizer/spec.md`

| 類型 | 存放位置 |
|------|---------|
| Daily Report | DB `reports` table（可 API 查詢） |
| Weekly Briefing | File system `briefings/weekly/YYYY-WNN.md` |

**問題**：
- Weekly briefing 無法透過 API 查詢，也無法在 dashboard 顯示
- MCP tool `get_weekly_summary` 直接讀 filesystem，假設 MCP server 與 briefing 檔案在同一台機器
- Docker 容器重啟後 filesystem 狀態遺失
- 兩種 briefing 用不同存儲機制，無法統一管理

---

### 5. 「原子性 mark-sent」邏輯導致 Email 重複發送

**相關 spec**：`digest-notifier/spec.md`

spec 要求：
> "If any channel fails, no posts are marked sent so the next digest run retries all channels with the same posts"

**問題**：
- Email 成功、Webhook 失敗 → posts 不標記 → 下次 digest 再跑一次
- Email 會**重複發送**給所有收件人
- 使用者看到重複 email，卻沒有任何 spec 說明如何處理

spec 完全沒有提到「partial delivery」的 UX 處理策略。

---

### 6. 啟動時自動觸發 Digest — crash loop 風險

**相關 spec**：`ai-summarizer/spec.md`

> "WHEN the backend starts (or restarts) AND no report has been generated in the past 23 hours THEN a digest is triggered immediately on startup"

**問題**：
- 服務 crash loop 或 rolling deploy 時，每次重啟都觸發 LLM API 呼叫
- 20 篇 × Groq/Gemini 呼叫，短時間內可能耗盡免費 quota
- Kubernetes/Docker Compose 的 health check 失敗 → 反覆重啟 → 反覆呼叫 API

---

### 7. Highlight Score 來源權重缺乏依據且影響過大

**相關 spec**：`weekly-briefing/spec.md`

```
highlight_score = relevance_score(0-10) * 0.5
               + source_weight(1-4) * 0.3
               + recency_decay(0/0.5/1.0) * 0.2
```

**問題**：
- 最高分：`10*0.5 + 4*0.3 + 1*0.2 = 6.4`
- ArXiv 文章（source_weight=4）比 Reddit（source_weight=1）永遠多 **0.9 分**（佔最高分的 14%）
- 一篇 ArXiv 的低品質論文（score=3）的 highlight_score = 3.1
- 一篇 Reddit 的高品質貼文（score=9）的 highlight_score = 4.8
- 結果：ArXiv 論文系統性排在 Reddit 貼文之前，與「精選」的語意不符
- spec 沒有提供這些權重的理論依據或 A/B 測試計畫

---

### 8. TF-IDF 在小語料庫下無意義

**相關 spec**：`relevance-scorer/spec.md`

spec 說：
> "TF-IDF is used to down-weight terms that appear extremely frequently across the corpus (IDF component)"

**問題**：
- 每天約 300–400 篇貼文，IDF 統計量不穩定
- 新部署時語料庫為空，IDF = 0，所有文章得分為 0
- spec 沒有說明：
  - IDF 語料庫是全歷史資料還是滑動時間窗？
  - 何時更新 IDF 模型？
  - 冷啟動時的 fallback 策略？

---

### 9. auto-refresh 的 `since` 參數語意錯誤

**相關 spec**：`news-dashboard/spec.md`

> "automatically poll `GET /api/news?since={last_fetched_at}` every 5 minutes"

**問題**：
- `last_fetched_at` 是系統最後一次抓取完成的時間（來自 `system_state`）
- 如果使用者離開 24 小時後回來，dashboard 會以「24 小時前」的 `last_fetched_at` 呼叫 API
- 回傳幾千筆資料，觸發大量渲染，導致前端效能問題
- 正確做法應該是「上次使用者看到的最新貼文時間」，由前端本地維護

---

## 三、過度理想化的設計（PM 觀點）

### 10. 評分閾值 threshold=5 過低且未說明調整機制

**相關 spec**：`relevance-scorer/spec.md`

> "The system SHALL expose a minimum score threshold (default: 5) for the `is_relevant` boolean flag"

`design.md` 另一處卻說：
> "Start at 7/10, tune after first week of data"

**問題**：spec 說 5，design.md 說 7，兩者不一致。
更重要的是，spec 完全沒有描述：
- 管理者如何即時調整 threshold 而不重啟服務？
- 修改 threshold 後，歷史資料是否重新標記 `is_relevant`？
- `digest_sent=True` 的舊文章如果 threshold 調高，是否會被重新納入下一次 digest？

---

### 11. `known_tools.txt` 維護機制不實際

**相關 spec**：`weekly-briefing/spec.md`

> "users or agents can request additions to `known_tools.txt` via PR"

**問題**：
- 要求一般使用者透過 PR 更新工具清單，完全不是 production 系統的正常流程
- AI 領域工具每週都有新工具出現，人工維護將嚴重落後
- 沒有說明 `known_tools.txt` 的初始內容從何而來、有多少條目
- `get_trending_tools` 的查詢結果品質完全取決於這份清單的覆蓋率，spec 沒有量化這個風險

---

### 12. LLM 判斷 `posted_at` 是不可靠的設計

**相關 spec**：`llm-agent-integration/spec.md`

> "`posted_at`: 原始發佈日（LLM 判斷）或今天"

**問題**：
- LLM 對日期的判斷本質上不可靠，可能產生幻覺
- 錯誤的 `posted_at` 會直接影響 `DIGEST_LOOKBACK_HOURS` 過濾邏輯
- 若 LLM 誤判為 3 年前的文章，該文章永遠不會出現在 digest 中
- spec 沒有任何 `posted_at` 合理性驗證（例如：不得早於系統上線日、不得晚於今天）

---

### 13. Bookmarks 搜尋行為前後矛盾

**相關 spec**：`bookmarks/spec.md`

Scenario「Search bookmarks by keyword」說：
> "GET /api/bookmarks?q=RAG... only bookmarks where the article title or note contains "RAG" are returned" （**server-side**）

Scenario「Dashboard bookmark UI」說：
> "WHEN the user types in the search box THEN the list is filtered **client-side** by article title or note content"

**問題**：同一份 spec 對書籤搜尋的實作位置前後矛盾。
後端工程師會以為要實作 server-side filtering，前端工程師會以為要做 client-side filtering，最終可能出現兩套邏輯並存。

---

### 14. Dashboard 分類過濾依賴 Markdown header parsing — 極脆弱

**相關 spec**：`news-dashboard/spec.md`

> "the filter is applied client-side by parsing the Markdown section headers"

**問題**：
- Report 的 Markdown header 包含 emoji（`## 🤖 AI Agent`）
- 任何格式調整（emoji 更換、標點、大小寫）都會讓 client-side parsing 靜默失效
- spec 沒有定義「parsing 規則」，前端實作必然是 hardcode 字串比對
- 這個設計讓 dashboard 功能與 LLM 輸出的 Markdown 格式強耦合

---

### 15. 多 Digest 收件人 + 原子性衝突

**相關 spec**：`digest-notifier/spec.md`

> "The recipient list SHALL be configurable via `DIGEST_EMAIL_TO`"

若 `DIGEST_EMAIL_TO` 包含多位收件人，且 SMTP 在發送第 3 個收件人時失敗：
- spec 的「原子性 mark-sent」規則要求：不標記任何 post
- 但前兩位收件人**已收到 email**
- 下次 digest 重跑，這兩位又收到重複 email

spec 對「部分 SMTP 成功」的情境完全沒有定義。

---

## 四、遺漏的關鍵需求

### 16. API Key 管理機制完全缺失

**相關 spec**：`news-api/spec.md`

spec 只說：
> "All endpoints except GET /api/health SHALL require a valid API key passed via the X-API-Key header"

但沒有任何關於：
- API key 如何產生？
- 儲存在哪裡（env var？DB？）？
- 如何輪換 / 撤銷？
- 是否支援多個 key（例如 dashboard 用一個、MCP server 用另一個）？

---

### 17. Reddit API 穩定性風險完全被低估

**相關 spec**：`multi-source-fetcher/spec.md`

spec 只備注 User-Agent 問題，但沒有提到：
- Reddit 在 2023 年大規模限制第三方 API 存取
- `/r/{subreddit}/new.json` 未認證存取隨時可能被 Reddit 關閉或限流
- spec 把這個不穩定 API 列為「primary source」，沒有任何降級或替代方案
- 沒有 circuit breaker 設計（只有「連續 3 次失敗跳過本次 cycle」，下個 cycle 又繼續嘗試）

---

### 18. 分數正規化公式從未定義

**相關 spec**：`relevance-scorer/spec.md`

> "The final score SHALL be computed as the sum of (term_weight × idf_factor) for each matched term, normalized to a 0–10 scale and clamped"

**問題**：「理論最大值」是多少？正規化公式是什麼？
若一篇文章包含所有 high-weight term（weight=3），加上 IDF 加乘，總和可能遠超 10。
spec 中的例子說「e.g., 8–10」，但沒有推導過程。開發者必須自己猜測正規化邊界。

---

## 五、總結評分

| Spec | 嚴重問題 | 中度問題 | 備注 |
|------|---------|---------|------|
| x-data-fetcher | ❌ 與設計文件直接矛盾 | — | 建議凍結或刪除 |
| relevance-scorer | — | 正規化未定義、TF-IDF 冷啟動 | |
| news-store | — | — | 相對完整 |
| digest-notifier | ❌ 重複發送 email | 多收件人部分成功 | |
| multi-source-fetcher | — | Reddit API 風險低估 | |
| news-api | ❌ 同步 digest 必 timeout | API key 管理缺失 | |
| news-dashboard | — | `since` 語意錯誤、Markdown parsing 脆弱 | |
| ai-summarizer | ❌ 同步 80s 阻塞、crash loop | 啟動觸發風險 | |
| arxiv-fetcher | — | 7 天 filter 無法設定 | 相對完整 |
| full-text-search | ❌ 索引欄位不存在 | — | |
| weekly-briefing | — | 權重設計、known_tools.txt 維護 | |
| bookmarks | — | 搜尋行為前後矛盾 | |
| llm-agent-integration | — | LLM 判斷日期不可靠 | |

**高優先修正**（會導致功能無法正常運作）：
1. FTS5 索引欄位對不上 schema（#3）
2. 同步 digest trigger 超時問題（#2）
3. 重複 email 發送（#5）
4. x-data-fetcher spec 凍結（#1）

**中優先修正**（會導致行為不符預期）：
5. 分數正規化公式補充（#18）
6. `since` 參數語意修正（#9）
7. Bookmarks 搜尋行為統一（#13）
8. Weekly briefing 存儲方式對齊 daily report（#4）

---

# Spec 審查補充 — strategy/ 文件

> 審查範圍：`strategy/product-review-2026-04-11.md` + `strategy/spec-v3.md`

---

## 六、product-review 與 spec-v3 的策略矛盾

### 19. 同一天產出的兩份文件，方向完全相反

這兩份文件都標注 `2026-04-11`，但核心方向打架：

| 議題 | product-review 說 | spec-v3 說 |
|------|------------------|------------|
| Hosted SaaS | P0 🔥「最高 ROI 的單一改動」 | **Out of Scope** |
| ArXiv | 降優先，「太學術，非主要用戶痛點」 | 重點功能，獨立「論文庫」分頁 + 週報子區塊 |
| 商業模式 | 訪談 CTO/VC，測試 $20-$99/mo pricing | Out of Scope |

**問題**：哪份文件代表最終決策？兩份文件同時存在，開發者不知道要跟哪個走。
沒有任何「決策依據」說明為何 spec-v3 推翻了 product-review 的結論。

---

## 七、spec-v3 的架構問題

### 20. RSS Fetcher 完全沒有 spec

**相關 spec**：`strategy/spec-v3.md` § 4.1

spec-v3 新增兩個 RSS 來源：
- Simon Willison's Blog
- swyx.io

但 `openspec/` 下**沒有任何** RSS fetcher 規格，也沒有：
- RSS 解析邏輯（Atom vs. RSS 2.0 格式差異）
- 如何對應到現有 `SourcePost` schema
- `content` 字段如何從 RSS `<description>` 或 `<content:encoded>` 提取
- Rate limit / polling 頻率
- 對應的 `sources.yaml` 格式範例

spec 只列出「新增資料來源」，沒有任何實作規格。

---

### 21. Hybrid Search 建立在有缺陷的 FTS5 之上

**相關 spec**：`strategy/spec-v3.md` § 4.4 + `full-text-search/spec.md`

v3 的 Hybrid Search 架構：
```
FTS5 結果集 A + 向量結果集 B → RRF 合併排名
```

但 v2 的 FTS5 spec（見審查問題 #3）有**欄位不存在的根本問題**：
- FTS5 索引 `title` + `summary` 欄位
- 但 DB schema 只有 `content` 欄位

v3 在 v2 的 broken FTS5 基礎上繼續疊加向量搜尋，等於在一個未完成的地基上蓋第二層。
v3 spec 沒有說明是否先修正 v2 FTS5 schema 問題。

---

### 22. Embedding 入庫時機對 fetch pipeline 的衝擊未評估

**相關 spec**：`strategy/spec-v3.md` § 4.4

spec 說：
> "每篇文章運算時間 約 20-50ms"

**問題**：
- 每個 fetch cycle 抓取 HN(100) + Reddit(100×4=400) + GitHub(30) + ArXiv(50) = **約 580 篇**
- 580 篇 × 50ms = **29 秒**額外 CPU 時間，發生在每次 fetch cycle 內
- spec 沒有說明 embedding 是同步還是非同步（是否阻塞 fetch pipeline？）
- 若是同步，原本 15 分鐘的 fetch cycle 增加近 30 秒，且第一次部署時要對歷史資料補算 embedding，可能需數分鐘

`sentence-transformers` 模型**第一次執行**需從 HuggingFace 下載 ~90MB。Docker build 時是否預先下載？spec 完全沒提到這個 cold start 問題。

---

### 23. `scoring.yaml` 與現有 `keywords.yaml` 的關係未定義

**相關 spec**：`strategy/spec-v3.md` § 4.5

spec-v3 新增 `config/scoring.yaml`（各維度評分權重），但現有 `relevance-scorer` 已有：
- `keywords.yaml`：high-weight(3) / standard-weight(1) 兩層關鍵字權重

**問題**：
- `scoring.yaml` 是**覆蓋** keywords.yaml 的權重？還是**疊加**到現有分數上？
- 如果某個 keyword 同時出現在兩個維度，分數計算邏輯是什麼？
- 這個設計等於出現了**兩套權重系統**，交互行為沒有被定義

---

### 24. 語言驗證邊界沒有明確規則

**相關 spec**：`strategy/spec-v3.md` § 4.2.1

spec 說：
> "偵測非中文字元（排除合理的英文術語），若觸發則標記並記錄"

**問題**：
- 什麼是「合理的英文術語」？
- `MCP`、`RAG`、`LangChain` → 應該排除
- `một`（越南文，spec 引用的真實案例）→ 應該觸發
- `multi-agent`、`fine-tuning`、`embedding` → 是否算英文術語？
- spec 只說「偵測非中文字元」，但沒有任何白名單規則或正則定義
- 實作者需要自己決定邊界，不同人實作結果不同

---

### 25. `get_posts_by_technique` 的 taxonomy 自動派生 → MCP 介面不穩定

**相關 spec**：`strategy/spec-v3.md` § 4.4 + § 8

spec-v3 的「架構決策」說：
> "taxonomy 從 `keywords.yaml` 群組名稱自動派生，不需額外維護"

**問題**：
- MCP tool 的 `technique` 參數有效值隨 `keywords.yaml` 的群組名稱異動而改變
- 若有人在 `keywords.yaml` 中重命名一個群組（例如 `ai_collaboration_techniques` → `collaboration`），呼叫 MCP tool 的所有 prompt/workflow 都會靜默失敗（查無結果）
- 對 **Claude Code 這類 AI caller** 來說，沒有固定的 schema 是嚴重問題 — AI 無法知道有效的 technique 值為何，必須先呼叫一個「列舉 technique」的 tool 才能使用

---

### 26. 成功指標無法被系統自動量測

**相關 spec**：`strategy/spec-v3.md` § 3.2

| 指標 | 標準 |
|------|------|
| 內容吸引力 | 每週至少 3 天的 briefing 有值得點開的內容 |

**問題**：
- 現有系統**沒有任何點擊追蹤**機制（dashboard 是 Next.js，briefing 是 `.md` 檔案）
- 「值得點開」是主觀判斷，無法自動量測
- 這個 KPI 只能靠人工觀察，不能成為 acceptance criteria
- spec 沒有說明如何量測，也沒有提出替代的客觀指標（例如：briefing 中至少 N% 文章 relevance_score ≥ 8）

---

### 27. ArXiv 每日 vs. 每週的切換對現有 pipeline 的衝擊未說明

**相關 spec**：`strategy/spec-v3.md` § 4.3

spec-v3 說：
> "每日 briefing 不包含 ArXiv 論文，論文歸入每週彙整"

但 `openspec/arxiv-fetcher/spec.md` 說 ArXiv 是每個 fetch cycle 都會運行的 source，產出的 posts 會進入 scoring pipeline 和 DB。

**問題**：
- v3 不是「停止抓 ArXiv」，而是「抓取但不放入每日 briefing」
- 這需要在 `BriefingGenerator` 中新增 source filter，但 spec 沒有說明如何實作
- 現有 `DIGEST_LOOKBACK_HOURS` 的 filter 是時間窗，不是 source filter
- v2 weekly-briefing spec 與 v3 的「每週論文摘要子區塊」之間的關係沒有釐清（是取代還是合併？）

---

## 八、strategy/ 文件的總結問題

| 文件 | 嚴重問題 | 中度問題 |
|------|---------|---------|
| product-review-2026-04-11.md | ❌ 與 spec-v3 策略方向互相矛盾，無決策機制 | ArXiv 優先級判斷與 spec-v3 相反 |
| spec-v3.md | ❌ RSS fetcher 無 spec、Hybrid Search 建在有缺陷的 FTS5 上 | Embedding cold start、scoring 雙重權重系統、語言驗證邊界 |

**需要在實作前先解決的問題**：
1. 釐清 product-review 與 spec-v3 之間的策略矛盾，確認最終方向（#19）
2. 補充 RSS Fetcher spec（#20）
3. 先修正 v2 FTS5 欄位問題，再建 v3 Hybrid Search（#21）
4. 定義 `scoring.yaml` 與 `keywords.yaml` 的交互關係（#23）
5. 為 `get_posts_by_technique` 提供穩定的 taxonomy 枚舉機制（#25）
