# Spec 審查討論記錄

> **狀態**：草稿，尚未定案
> **來源**：`openspec/spec-review.md` + 四人跨部門審查會議（內部：蘇雅婷、林志遠 / 外部：陳建宏、張雅琳）
> **最後更新**：2026-04-12
> **注意**：本文件不修改任何現有 spec，所有「決策」需確認後才能落地

---

## 一、程式碼現狀確認（2026-04-12 實際查驗）

在討論任何改動前，先確認三個關鍵事實。

### 事實一：Threshold 確認是 5.0（未曾調整）

- `config.py:40` → `relevance_threshold: float = 5.0`
- `relevance_scorer.py:80` → `DEFAULT_KEYWORDS` 裡 `"threshold": 5`
- `design.md` 說「Start at 7/10, tune after first week of data」，但從未執行

**實際含義**：只要命中 2 個 high-weight 詞（raw=6）就進 briefing，門檻非常低。

**用戶決策**：threshold 暫不調整，等其他改動完成、觀察結果後再評估。

---

### 事實二：FTS5 並沒有壞掉（spec-review #3 判斷有誤）

`migration 006` 的實際 SQL：
```sql
-- 開發者用 workaround：沒有 title 欄位，就用 content 前 100 字元代替
INSERT INTO articles_fts(rowid, title, summary)
SELECT id, substr(content, 1, 100), COALESCE(summary_zh, '')
FROM posts
```

觸發器也使用相同映射，FTS5 是運作的。

**修正**：spec-review #3「FTS5 索引欄位不存在」的判斷有誤。不是 production bug，而是 spec 描述和實作不一致——開發者選擇了務實的 workaround，但沒有在 spec 裡說明。

**需要的行動**：在 spec 補充說明「workaround 為有意設計」，而非修復。

---

### 事實三：TF-IDF 從未被實作（spec-review #8 問題不存在）

`relevance_scorer.py` 的實際邏輯：
```python
# 沒有任何 IDF 計算
raw_score += 3   # high_weight 命中
raw_score += 1   # standard_weight 命中
score = min(10.0, raw_score)               # 截斷，不是正規化
score = min(10.0, score + min(points/100, 3.0))  # 社群投票加分 max +3
```

完整評分公式：
```
score = min(10, Σ(命中詞 × 權重) + min(社群票數/100, 3))
```

**修正**：
- spec-review #8（TF-IDF 冷啟動問題）不存在，TF-IDF 從未實作
- spec-review #18（正規化公式未定義）實際就是截斷，公式非常簡單

**需要的行動**：將所有 spec 裡的「TF-IDF」描述改為「keyword weight scoring」，補充實際公式。

---

## 二、問題重新分類（根據實際程式碼修正）

### 已確認可移除或降級的 spec-review 問題

| # | 原判斷 | 修正後狀態 |
|---|--------|-----------|
| #3 | FTS5 索引欄位不存在 🔴 | 降級為 🟡「spec 描述不準確，需補充 workaround 說明」 |
| #8 | TF-IDF 冷啟動問題 | **移除**，TF-IDF 從未實作，問題不存在 |
| #18 | 正規化公式未定義 | 降級為 🟡「補充說明公式即可（截斷至 10）」 |

---

## 三、已確認的決策

### A 類：v2 現有架構問題

| # | 問題 | 決策 |
|---|------|------|
| #2 | POST /api/digest/trigger 同步超時（80秒） | 改為 202 Accepted + job_id 非同步模式 |
| #3 | FTS5 spec 描述與實作不一致 | 補充 spec 說明 workaround，不修改實作 |
| #5 #15 | Email 重複發送 | 各 channel 獨立 flag（email_sent / webhook_sent），新增 migration |
| #1 | x-data-fetcher spec 與設計文件矛盾 | 在 spec 頂部加凍結標記，保留記錄但不實作 |
| #6 | Crash loop 觸發 LLM API | 加 30 分鐘 startup cooldown |
| #9 | dashboard `since` 參數語意錯誤 | 改由前端 localStorage 本地維護 |

### B 類：v3 spec 設計缺口

| # | 問題 | 決策 |
|---|------|------|
| #7 | Highlight score ArXiv 偏權（ArXiv 已移出每日 briefing） | 重新設計每日 highlight_score，移除 arxiv source_weight，或每日 highlight 只在非 ArXiv 文章中計算 |
| #8 | TF-IDF 冷啟動 | **移除**，問題不存在 |
| #10 | Threshold 5 vs 7 矛盾 | 暫不調整（用戶決策），等 Group 1 其他改動完成後觀察結果 |
| #11 | known_tools.txt 維護不實際 | 改從 DB 動態派生（擷取 posts 中出現的 tool 名稱） |
| #12 | LLM 判斷 posted_at 不可靠 | 加合理性驗證：不早於系統上線日、不晚於今天 |
| #13 | Bookmarks 搜尋前後矛盾 | 統一為 server-side filtering |
| #14 | Dashboard 分類依賴 Markdown header parsing | 改用 DB `labels` 欄位，廢棄 Markdown parsing |
| #17 | Reddit API 穩定性風險低估 | 補充 circuit breaker 設計，加 Reddit 失敗時的降級策略說明 |
| #18 | 正規化公式未定義 | 補充說明實際公式（截斷至 10） |
| #19 | product-review 與 spec-v3 策略矛盾 | 在 product-review 頂部加備注，spec-v3 為準 |
| #20 | RSS Fetcher 沒有 spec | 補充獨立 RSS Fetcher spec |
| #21 | Hybrid Search 建在有缺陷的 FTS5 上 | FTS5 實際是運作的（#3 已修正），但實作順序仍維持：確認 FTS5 品質 → 建向量搜尋 → RRF 合併 |
| #22 | Embedding 入庫阻塞 fetch pipeline | 非同步 background worker + server 啟動時 warmup |
| #23 | scoring.yaml 與 keywords.yaml 雙重權重 | 明確分層：keywords.yaml 管詞彙權重，scoring.yaml 管維度呈現優先序 |
| #24 | 語言驗證邊界不明確 | Unicode block 判斷（允許 CJK + Basic Latin） |
| #25 | get_posts_by_technique taxonomy 不穩定 | 新增 list_techniques() MCP tool 提供枚舉介面 |
| #26 | 成功指標無法自動量測 | 改為客觀指標：relevance_score ≥ 7 的文章佔比 ≥ 40% |
| #27 | ArXiv 每日/每週切換衝擊未說明 | BriefingGenerator 加 source filter，每日排除 arxiv |

### C 類：策略矛盾

| # | 問題 | 決策 |
|---|------|------|
| #19 | product-review 與 spec-v3 方向相反 | product-review 為初期探索，spec-v3 為最終方向，加備注說明 |

---

## 四、功能優先序（確認版）

### Group 1：直接改善每日 briefing 體驗（先做）

這些改動用戶每天都感受得到，且不需要大型架構改動：

| 項目 | 對應問題 | 類型 |
|------|---------|------|
| 擴充 keywords（加入 AI 協作技巧維度） | spec-v3 § 4.1 | 內容策展 |
| Briefing 結構重設計（4 個維度分區） | spec-v3 § 4.2.2 | 呈現格式 |
| 語言驗證修復（亂碼 / 混語） | spec-v3 § 4.2.1 | 品質保證 |
| Highlight score 重新設計（移除 ArXiv 偏權） | #7 | v2 bug |
| Digest 改非同步（202 Accepted） | #2 | v2 bug |
| Email 各 channel 獨立 flag | #5 #15 | v2 bug |
| Crash loop cooldown | #6 | v2 bug |
| Spec 與 code 對齊（移除 TF-IDF 描述） | #8 #18 | 文件修正 |
| x-data-fetcher spec 加凍結標記 | #1 | 文件修正 |

**threshold 暫不調整**，等 Group 1 完成後觀察 briefing 品質變化再決定。

---

### Group 2：架構能力建設（Group 1 穩定後再做）

這些改動對用戶當前體驗影響較小，但有長期價值：

| 項目 | 對應問題 | 類型 |
|------|---------|------|
| RSS Fetcher（Simon Willison 等） | #20 | 新資料來源 |
| 新增 Reddit subreddits（ClaudeAI 等） | spec-v3 § 4.1 | 新資料來源 |
| Hybrid Search（FTS5 + 向量 + RRF） | spec-v3 § 4.4 | 架構 |
| Embedding pipeline（非同步 + warmup） | #22 | 架構 |
| list_techniques() MCP tool | #25 | MCP |
| ArXiv 每週論文摘要子區塊 | spec-v3 § 4.3 | 呈現 |
| ArXiv web dashboard source filter | spec-v3 § 4.3 | 前端 |
| known_tools.txt 改動態派生 | #11 | 重構 |
| LLM posted_at 合理性驗證 | #12 | 防護 |
| Bookmarks 搜尋統一 server-side | #13 | 修正 |
| Dashboard 分類改用 labels 欄位 | #14 | 前端 |

---

## 五、開放問題（還沒有答案的）

| 問題 | 說明 |
|------|------|
| Hybrid Search RRF 實作細節 | FTS5 rank 與向量相似度的 scale 不同，k 值未定，合併邏輯未定 |
| Embedding worker 的並發機制 | CPU-bound 任務在 FastAPI async context 的正確處理方式（run_in_executor vs subprocess） |
| RSS polling 頻率獨立設定 | RSS 來源不需要 15 分鐘 poll 一次，需要獨立的 polling cadence 設定 |
| Dashboard `since` 參數改動的向後相容 | 改為前端 localStorage 後，現有 auto-refresh 邏輯需要同步修改 |

---

## 六、下一步

1. **確認本文件內容無誤** → 用來更新 spec-v3.md 和相關 spec
2. **撰寫實作計劃** → 依 Group 1 → Group 2 順序排定任務和依賴關係
3. **threshold 決策** → 等 Group 1 完成後，觀察 briefing 品質，再決定是否從 5 調至 7

---

*本文件為討論草稿。所有決策需更新至正式 spec 後才能進入實作。*
