# Briefing 品質改善計劃

**建立日期**：2026-04-13
**完成日期**：2026-04-14
**狀態**：✅ 三個 Phase 全部完成並 commit
**依據**：Briefing 輸出品質驗證（2026-04-12 ~ 2026-04-13）
**問題總結**：原始文章品質足夠，但 LLM 沒有足夠資訊選出最有價值的內容，且摘要品質低導致洞察力流失

---

## 診斷修正

先前識別的「三個問題」在深入看程式碼後需要修正：

| 原診斷 | 實際狀況 | 調整 |
|--------|---------|------|
| `summary_zh` 為 null | 摘要在 `_run_summarization()` 中生成，briefing 執行時 summary 已存在 | 問題不是「null」，是摘要**品質差**（一行通泛描述） |
| 同分文章 LLM 在猜 | 確認：12+ 篇 score=10.0，報告中無次要排序依據 | 維持，需要語意二次排序 |
| Prompt 重寫 | 確認，但 prompt 問題是下游症狀，上游摘要品質才是根因 | 調整優先序：先修摘要，再修 prompt |

---

## 根本原因分析

```
get_unsent_relevant_posts(top 20, score DESC)
    ↓
[所有文章 score=10.0，無法區分]
    ↓
summarize_batch()  ← 問題 1：one-liner 摘要，無技術洞察
    ↓
assemble_report()  ← 問題 2：按 label 分組（ai-agent/model/tool），
                      與 briefing 四維度不對齊，且未傳達 source 性質差異
    ↓
_BRIEFING_PROMPT   ← 問題 3：沒有選文準則，LLM 用格式整齊度而非價值做選擇
    ↓
Briefing 輸出通泛，最有價值的 Reddit 討論串未被選中
```

---

## Phase A：摘要品質改善

**目標**：讓每篇文章的 `summary_zh` 包含技術洞察，而不只是功能描述。

**改動範圍**：`backend/app/summarizer/groq_client.py`（或對應的 `_SUMMARIZE_PROMPT`）

### 現狀

```
prompt: "請用繁體中文摘要以下文章"
output: "Synapse 是一個開源平台，允許創建和連接由 LLM 驅動的人工智慧代理。"
```

### 目標輸出格式

```
[是什麼] 一句話描述核心技術/方案
[解決什麼] 具體痛點，或和現有方案的差異
[為何值得注意] 一個讓工程師想點進去的理由
```

範例：
```
Token exhaustion 實戰討論：用 Claude Sonnet 4.5 + Playwright 做 browser automation，
在多步驟任務中遇到 context 爆滿問題。作者分享的具體策略是用 checkpoint summarization
分段壓縮 context，而非依賴 sliding window。
值得看：這個方法在 Claude Code 的長任務中同樣適用。
```

**注意**：
- Reddit 討論串的 `content` 欄位包含完整貼文內容，應使用完整 content 生成摘要，而非截斷
- GitHub repo 的 content 通常就是 description（簡短），摘要應補充「這個工具解決什麼設計決策問題」
- 摘要長度上限從目前的 ~50 字放寬到 ~120 字

---

## Phase B：二次語意排序

**目標**：在 20 篇同分（score=10.0）文章中，優先選出與使用者工作 context 最相關的。

**改動範圍**：`backend/app/notifier/digest_notifier.py` 中的 `generate_digest()` 流程

### 現狀

```python
# 純 relevance_score DESC 排序，同分文章順序不確定
get_unsent_relevant_posts(limit=20, since=since)
```

### 目標

```
Step 1：取 top 40 篇（擴大候選池）
Step 2：若 FEATURE_EMBEDDINGS=true 且 USER_CONTEXT 非空：
    對 USER_CONTEXT 做 embed → cosine similarity 對 40 篇做二次排序
Step 3：取二次排序後的 top 20 進入摘要和 briefing
Step 4：若 FEATURE_EMBEDDINGS=false：維持原本行為（top 20 by relevance_score）
```

**USER_CONTEXT 設定範例**（放在 .env）：
```env
USER_CONTEXT=I am building AI agents with Claude. Interested in context management,
multi-agent orchestration, MCP server design, and practical agentic workflows.
```

**二次排序公式**：
```
final_score = relevance_score * 0.6 + cosine_similarity(post_embedding, context_embedding) * 10 * 0.4
```

- `relevance_score` 仍有主導權（60%），避免完全跳過高關鍵字命中的文章
- 語意相似度放大到 0–10 scale（× 10）再加權

---

## Phase C：Report 格式與 Briefing Prompt 改善

**目標**：讓 briefing LLM 看到更有用的資訊，並給出明確的選文準則。

### C1：`assemble_report()` 格式調整

**改動範圍**：`backend/app/summarizer/summary_generator.py`

現狀 format：
```markdown
- **Build AI agents that actually do things...** (`GitHub`)
  Synapse 是一個開源平台...
  🔗 [原文](https://...)
```

目標 format（增加 source 性質標記和分數）：
```markdown
- **[討論] Build AI agents...** (`Reddit` ▲ 847) score=10.0
  [摘要內容]
  🔗 [原文](https://...)
```

新增的標記邏輯：
- `[討論]`：source=reddit 且 content 包含第一人稱或問句
- `[實測]`：content 包含 benchmark/comparison/test result 關鍵字
- `[工具釋出]`：source=github，無上述特徵
- `[新聞]`：HN 或 Reddit，content 包含公司/模型名稱

**為什麼**：讓 briefing LLM 在選文時能區分「有人分享實戰心得」和「又一個 GitHub 工具」。

### C2：`_BRIEFING_PROMPT` 改寫

**改動範圍**：`backend/app/briefing/briefing_generator.py`

核心修改三點：

**1. 明確選文準則（依優先序）**

```
選文準則（依優先序）：
1. 優先選 [討論] 和 [實測] 類型：描述具體問題和解法的貼文比功能公告有更高閱讀價值
2. 優先選有具體技術細節的（說出了具體方法、數字、或讓人意外的發現）
3. 同等情況下，選 points/votes 較高的（代表社群認為有價值）
4. 避免選只列出功能清單、沒有技術洞察的工具公告
```

**2. 每條描述的品質要求（附壞範例）**

```
每條說明必須：
- 說出「具體的技術方法或發現」，不是泛稱功能
- 說出「和其他方案不同的地方」，或「讓工程師意外的點」

禁止的寫法（以下是反例，不得使用）：
✗ "這可以幫助開發者更有效地開發 AI 應用程式"
✗ "展示了 AI 技術的創新和多樣性"
✗ "具有重要意義"
✗ "值得注意"（單獨作為結尾）
```

**3. 禁止跨維度重複**

```
規則：每篇文章只能出現在一個維度。
若同時符合多個維度，放在最主要的那個。
```

**格式固定為條列**（不允許段落），每維度 2–4 個 bullet point。

---

## 改動檔案清單

| 檔案 | 改動 | Phase |
|------|------|-------|
| `backend/app/summarizer/groq_client.py` | 改善 summarize prompt，要求三段式輸出 | A |
| `backend/app/notifier/digest_notifier.py` | `generate_digest()` 擴大候選池 → 語意二次排序 | B |
| `backend/app/embeddings/vector_search.py` | 新增 `rank_by_user_context()` 函式 | B |
| `backend/app/summarizer/summary_generator.py` | `_format_post_entry()` 加 source 類型標記 | C1 |
| `backend/app/briefing/briefing_generator.py` | 改寫 `_BRIEFING_PROMPT` | C2 |
| `backend/tests/test_briefing_generator.py` | 更新 prompt 相關測試 | C2 |
| `backend/tests/test_digest_notifier.py` | 新增二次排序測試 | B |

---

## 執行順序與驗證方式

```
Phase A → commit → 手動觸發 digest，看 summary_zh 品質是否改善
Phase B → commit → 確認 USER_CONTEXT 設定後，二次排序是否把 Reddit 討論串拉上來
Phase C → commit → 重新生成今天 briefing，人工判斷是否有想點進去的內容
```

### Phase A 驗證標準
- 新生成的 `summary_zh` 長度 ≥ 80 字（原本約 30–50 字）
- 包含「解決什麼問題」的描述，不只是「是什麼」

### Phase B 驗證標準
- 有設 `USER_CONTEXT` 的情況下，進入 briefing 的 top 20 中，Reddit 討論串數量 ≥ 3（原本通常 0–1）

### Phase C 驗證標準（人工）
- 讀完 briefing 後，至少有 1 篇想點進去看原文
- 無「可以幫助開發者...」模板句
- 無跨維度重複文章

---

## 不改動的部分

- `relevance_score` 計算邏輯（threshold 5.0 維持觀察期）
- Highlight scorer 的 source weight（reddit:1 vs github:3 是另一個獨立問題）
- Embedding pipeline 架構
- 任何 API 端點
