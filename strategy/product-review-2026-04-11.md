# AI News Radar — 產品競爭評估報告

> **[歷史文件]** 本文為 2026-04-11 初期探索討論的記錄，當時尚未確認用戶目標。
> 後續確認：用戶目標為開源練習與技術探索，非商業化。
> **最終方向以 `strategy/spec-v3.md` 為準**，本文件的商業化建議（SaaS、Pricing 等）均不採用。

**日期**: 2026-04-11
**會議性質**: 跨職能產品評估
**背景**: 產品上線後競爭表現不如預期，需重新評估定位與規劃方向

---

## 一、產品現況快照

| 維度 | 現狀 |
|------|------|
| 核心功能 | 多源 AI 新聞聚合（HN / Reddit / GitHub / ArXiv）+ MCP Server + 每日中文簡報 |
| 技術架構 | FastAPI + Next.js + SQLite/PostgreSQL，self-hosted |
| 部署方式 | Docker Compose 或 Local Dev，需手動設定 .env + Alembic |
| 差異化功能 | MCP Server（可在 Claude 對話中直接查詢個人新聞庫）、Traditional Chinese briefing |
| 商業模式 | 純 open source，無 SaaS、無 pricing |
| 測試狀態 | 180 tests pass，Alembic migration 007 |

---

## 二、競品比較

| 競品 | 優勢 | AI News Radar 的差距 |
|------|------|---------------------|
| Feedly AI | 零部署、UI 成熟、行動端支援 | 需要 Docker + CLI |
| The Rundown AI | Newsletter 訂閱即用，50 萬+ 訂閱者 | 獲客路徑為零 |
| tldr;ai | 每日精簡、email 推送開箱即用 | email digest 需自設 SMTP |
| Perplexity | 任何問題即時查，無需前置作業 | 需先建立本地資料庫才能使用 |

---

## 三、根本問題診斷

> **產品本身有技術價值，但缺少從「技術展示」到「市場產品」的那一步。**

### 3.1 門檻問題（最高優先）

- Self-hosted 架構淘汰了約 95% 的潛在用戶
- 從 README 到第一個有用的 briefing，需要跑 CLI、設定 .env、執行 migration
- 沒有 onboarding flow，新用戶不知道「第一個 Wow moment」在哪裡

### 3.2 定位模糊

- 現有定位「self-hosted multi-source AI news aggregator」對目標用戶沒有明確說明痛點
- MCP Server 是最強的差異化功能，卻藏在 README 中段，不是主打訴求
- 缺乏明確 ICP（理想客戶輪廓）

### 3.3 缺乏傳播機制

- 所有資料在用戶本地，沒有辦法 share briefing
- 沒有 word-of-mouth 的觸發點
- 純 open source 沒有 lead capture 機制

---

## 四、各角色評估重點

### 保守型市場調查員
- 需要以數據驗證 PMF，GitHub Stars 是目前最可靠的指標
- 建議先鞏固技術型 early adopter，不要在 PMF 未驗證前投入行銷資源
- 缺乏 mobile app 是長期硬傷

### 積極型市場調查員
- MCP Server 是這個時代最被低估的分發管道，現在是時機窗口
- 真正未被佔領的利基：「給 AI builder 的競品情報工具」
- 企業購買力存在（AI 新創 CTO、VC 分析師），現有競品都無 MCP 整合
- 立即做 hosted SaaS 是最高 ROI 的單一改動

### 市場趨勢分析師
- MCP 生態正在快速爆炸，6 個月後會有資金充足的競品進場
- Gartner 預測 2026 年 60% 企業將有專職 AI Technology Scout 角色，需要 queryable 情報工具
- Newsletter 市場飽和，但 queryable + persistent knowledge base 市場仍空白

### 業務
- 三大成交障礙：部署門檻、缺乏 Wow moment、無分享機制
- 高價值潛在買家：AI 新創技術 co-founder、VC 分析師、大廠 AI 戰略部門、AI 媒體編輯
- 需要 hosted free tier + email lead capture + public share link

### PM
- 重新定義一句話定位：**「給 AI builder 的即時情報工具 — 可以在 Claude 裡直接查詢你的個人 AI 新聞庫」**
- 現有用戶旅程有嚴重摩擦，需要重新設計 onboarding
- 功能太多但核心 value proposition 不清晰

### 軟體架構師
- SaaS 化技術可行，預估 3-4 週可上 hosted beta
- Embedding pipeline 應提前至 v2.5（現排在 v3 太晚）
- 需加 per-user API key 機制、rate limiting、user_id FK 資料隔離

---

## 五、功能優先級重排

| 優先級 | 功能 | 理由 |
|--------|------|------|
| P0 🔥 | Hosted 版本（Railway/Render，無部署需求） | 解鎖 95% 被門檻擋住的用戶 |
| P0 🔥 | Onboarding flow + 空狀態引導 | 建立第一個 Wow moment |
| P1 | Public share link（briefing / weekly report） | 病毒傳播機制 |
| P1 | Embedding semantic search | 真正的搜尋差異化 |
| P1 | Browser extension（一鍵加入知識庫） | 提升資料多樣性與用戶黏性 |
| P2 | Team workspace（shared knowledge base） | 商業化路徑 |
| P2 | Stripe billing | 收費機制 |
| P3 | Mobile app | 消費場景擴展 |
| 降優先 | ArXiv fetcher（現有功能） | 太學術，非主要用戶痛點 |

---

## 六、產品路線圖修正

```
v2（已完成）
  多源聚合 + MCP Server + 每日簡報 + 書籤 + FTS5 搜尋

v2.5（目標：4-6 週內）
  - Hosted free tier（Railway/Render 一鍵部署）
  - Onboarding flow + 空狀態設計
  - Public briefing share link
  - Embedding semantic search（pgvector）
  - Landing page 重寫 + 定位調整
  - MCP Server per-user auth

v3（目標：Q3 2026）
  - Team workspace + shared knowledge base
  - Official changelog RSS（OpenAI / Anthropic / Google）
  - Stripe billing（Individual $20/mo, Team $99/mo）
  - Browser extension

v4（目標：Q4 2026）
  - Enterprise plan（SSO、audit log、自訂資料源）
  - Mobile companion app
  - 個人化推薦模型
```

---

## 七、三大立即行動

### 行動 1：移除門檻（最高優先）
- **目標**：用戶不需接觸任何 CLI 即可體驗完整功能
- **做法**：部署 hosted 版本，提供 free tier
- **時程**：3-4 週
- **預期效果**：轉化率從 ~5% 提升至 ~40%

### 行動 2：重新定位與品牌認知
- **目標**：讓 MCP integration 成為 headline，而非 feature
- **做法**：重寫 landing page / README，定位為「給 AI builder 的競品情報工具」
- **配合**：加 public share link，讓 briefing 可傳播

### 行動 3：驗證商業模式
- **目標**：在擴大開發前先有 10 個付費用戶
- **做法**：訪談 5-10 個 AI 新創 CTO / VC 分析師，測試 pricing
- **測試 pricing**：Individual $20/mo，Team $99/mo

---

## 八、待深入討論的議題

以下議題需要進一步細節討論：

1. **SaaS 架構設計細節** — 多用戶隔離、auth 機制、資料安全
2. **Embedding pipeline 技術選型** — pgvector vs. sqlite-vss vs. 外部服務
3. **Onboarding UX 設計** — 從 sign-up 到第一個 Wow moment 的完整流程
4. **Pricing 策略** — Free tier 邊界、Individual vs. Team 功能差異
5. **Browser Extension 規格** — 支援的來源、與知識庫的整合方式
6. **Go-to-market 策略** — 如何在 MCP 時機窗口內建立品牌認知
7. **ICP 定義與驗證方法** — 如何找到並訪談目標用戶

---

*本文件由跨職能評估會議產出，後續細節討論請基於本文件展開。*
