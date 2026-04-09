# GitHub 開源發佈規劃

**文件版本**：1.2  
**建立日期**：2026-04-09  
**最後更新**：2026-04-09  
**審閱團隊**：PM、業務、工程

---

## 目前進度總結（2026-04-09）

### ✅ 已完成

| Phase | 內容 | 完成日期 |
|-------|------|----------|
| Phase 1 | 內容清理（.gitignore、LICENSE、CONTRIBUTING、敏感資料移除） | 2026-04-09 |
| Phase 2 | README 優化（badges、MCP 說明、Roadmap、架構圖） | 2026-04-09 |
| Phase 3 | 專案改名 `ai-news-radar` | 2026-04-09 |
| Phase 4 | GitHub repo 建立、程式碼推送、Topics、Release v1.0.0、CI、Issue Templates | 2026-04-09 |

**Repo 已公開**：https://github.com/pursky7468/ai-news-radar  
**Release**：https://github.com/pursky7468/ai-news-radar/releases/tag/v1.0.0

### ⏸ Pending（暫緩）

| 項目 | 說明 |
|------|------|
| Demo GIF / Screenshot | 需實機錄製，待安排時間製作 |
| 社群推廣（HN / Reddit / Twitter） | 已取消，不在目前執行範圍 |

---

## 一、團隊角色與職責

| 角色 | 職責範圍 |
|------|----------|
| **PM**（Product Manager） | 產品定位、功能優先級、Roadmap 規劃、社群需求收集 |
| **業務**（Business Analyst） | 市場分析、競品研究、目標用戶畫像、開源策略 |
| **工程**（Engineer） | 技術實作、程式碼品質、文件撰寫、CI/CD 設定 |

---

## 二、市場環境分析（業務視角）

### 2.1 總體市場規模

- AI 開發工具市場 2026 年估值達 **$128 億美元**（2024 年 $51 億，2 年內 2.5 倍成長）
- GitHub 上 AI 相關 repo 超過 **430 萬個**，YoY 成長 178%
- **84%** 的開發者表示正在使用或計劃使用 AI 工具
- **56%** 的工程師有 70% 以上的工作由 AI 輔助完成

### 2.2 MCP 生態系成長（關鍵趨勢）

MCP（Model Context Protocol）是本專案最重要的差異化因素之一：

- MCP server 下載量：2024/11 的 10 萬次 → 2025/04 的 **800 萬次**（5 個月 80 倍）
- 目前已有 **5,800+ MCP servers**，300+ MCP clients
- OpenAI（2025/03）、Google DeepMind（2025/04）、Microsoft 相繼採用
- 2025/12 MCP 捐贈給 Agentic AI Foundation，成為 **廠商中立的業界標準**
- **2026 年是 MCP 企業落地元年**

> 本專案已是少數同時具備「多源資料聚合 + MCP 整合」的開源工具，與 MCP 生態系成長直接掛鉤。

### 2.3 目標用戶畫像

| 用戶類型 | 需求描述 | 規模估計 |
|----------|----------|----------|
| **重度 Claude 用戶** | 希望在 Claude 中直接查詢 AI 新聞，無需切換工具 | MCP 早期採用者，成長中 |
| **AI 開發者 / Indie Hacker** | 需要每日追蹤 LLM、Agent 框架最新動態 | GitHub 上數百萬 AI repo 作者 |
| **中文技術社群** | 需要高品質繁中 AI 技術摘要，目前資源稀缺 | 台灣、香港、海外華人工程師 |
| **研究人員** | 追蹤 ArXiv 論文 + 社群討論的交叉點 | cs.AI/cs.LG 訂閱者 |

---

## 三、現有開源競品分析（業務 + PM 視角）

### 3.1 直接競品

| 專案 | 核心功能 | 差距分析 |
|------|----------|----------|
| [AI-News-Briefing](https://github.com/hoangsonww/AI-News-Briefing) | Claude CLI 搜尋網路 → Notion | 無本地資料庫；每次重新搜尋，無累積；無評分系統；無 MCP |
| HN MCP Server（各種） | 單純抓 HN 資料的 MCP server | 單一來源；無評分；無儲存；無 briefing |
| ArXiv MCP Server（各種） | 搜尋 ArXiv 論文的 MCP server | 單一來源；無社群訊號整合 |
| Real-time AI Aggregator（商業） | 30+ 來源聚合 + 品質評分 | **不開源**；無 MCP；無中文 |
| Reddit News Agent (MCP+ADK) | Reddit 抓取 + MCP | 單一來源；無 briefing；無評分 |

### 3.2 本專案的差異化定位

```
「持續累積本地 AI 知識庫 + MCP 整合」
vs.
「每次重新搜尋網路的一次性 briefing」
```

**唯一同時具備以下全部功能的開源工具**：

- 多源聚合（HN + Reddit + GitHub + ArXiv）
- 本地評分系統（無需 LLM API，零成本運作）
- 持久化資料庫（SQLite / PostgreSQL）
- REST API + Next.js Dashboard
- **MCP Server**（Claude 直接查詢）
- 繁體中文 AI 日報 / 週報自動生成

### 3.3 市場空缺總結

> GitHub 上目前**沒有**一個專案能讓開發者「自架一個持續學習的 AI 新聞知識庫，並直接在 Claude 中查詢」。這是本專案的核心護城河。

---

## 四、GitHub 發佈規劃（PM 視角）

### 4.1 發佈前準備清單

#### Phase 1 — 內容清理（工程）✅ 完成

- [x] 確認 `.env.example` 無真實金鑰（已確認安全）
- [x] 將 `openspec/product-feedback.md` 從 git 歷史移除（`git filter-branch` 重寫 34 個 commit）
- [x] 新增 `LICENSE`（MIT）
- [x] 新增 `CONTRIBUTING.md`（貢獻指南）
- [x] 確認 `.gitignore` 完整（已更新：排除 test-results/、.claude/、tsconfig.tsbuildinfo）
- [x] 新增 `.github/ISSUE_TEMPLATE/`（bug report + feature request）

#### Phase 2 — README 優化（PM + 工程）✅ 完成

- [x] 加入 `## Why this project?`（30 秒電梯簡報）
- [x] 加入 `## Roadmap` 區塊（v1 ✅ / v2 🚧 / v3 📋）
- [x] 加入 Badge（License、Python version、Tests passing、MCP）
- [x] 加入 MCP 設定說明（完整 setup guide + 5 個工具列表）
- [x] 更新架構說明（加入 ArXiv 第四資料來源）
- [x] 補充 bookmarks API 端點
- [ ] 加入 **Demo GIF / Screenshot** — ⏸ Pending（需實機錄製）

#### Phase 3 — 專案名稱與定位（PM + 業務）✅ 完成

- [x] 改名為 `ai-news-radar`（package.json name + description 已更新）
- [x] README 標題與副標題更新

#### Phase 4 — 推上 GitHub ✅ 完成（2026-04-09）

- [x] 所有變更已 commit，本地 git 歷史乾淨
- [x] 安裝 gh CLI
- [x] `gh auth login`
- [x] `gh repo create ai-news-radar --public` → https://github.com/pursky7468/ai-news-radar
- [x] `git remote add origin` + `git push -u origin master`
- [x] 設定 Repository Topics（ai, mcp, fastapi, nextjs, llm, claude, hacker-news, self-hosted）
- [x] 建立 Release Tag `v1.0.0` → https://github.com/pursky7468/ai-news-radar/releases/tag/v1.0.0
- [x] 新增 `.github/ISSUE_TEMPLATE/`（bug report + feature request）
- [x] 新增 `.github/workflows/ci.yml`（GitHub Actions CI）

### 4.2 發佈策略（業務視角）⏸ Pending

> **狀態說明**：社群推廣（HN / Reddit / Twitter）已暫緩，不在目前執行範圍內。
> 待 Demo GIF 完成後再評估是否啟動。

#### 目標平台與時機（保留供未來參考）

| 平台 | 發佈策略 | 預期效果 | 狀態 |
|------|----------|----------|------|
| **Hacker News** | 週二或週三早上（美東時間）發 Show HN | 最高曝光；觸達核心 AI 開發者族群 | ⏸ Pending |
| **Reddit r/MachineLearning** | 同步發文，強調 ArXiv 整合 | 研究人員族群 | ⏸ Pending |
| **Reddit r/LocalLLaMA** | 強調 MCP + Claude 整合，自架隱私性 | 本地部署愛好者 | ⏸ Pending |
| **Twitter/X** | Demo 影片 + MCP 功能截圖 | 擴散效果 | ⏸ Pending |
| **awesome-mcp-servers** | 提交 PR 加入清單 | 長期曝光，MCP 生態系入口 | ⏸ Pending |

### 4.3 發佈時程（已更新）

```
Week 1（4/9）   ✅ Phase 1–4 全部完成，repo 已公開
                   github.com/pursky7468/ai-news-radar
Week 2+         ⏸ Demo GIF 製作（Pending）
                ⏸ 社群推廣（Pending，取消）
```

---

## 五、成功指標（PM 定義）

### 上線後 30 天目標

| 指標 | 目標 | 說明 |
|------|------|------|
| GitHub Stars | 200+ | HN Show HN 成功的基準 |
| Fork 數 | 30+ | 實際部署使用的代理指標 |
| Issue 數 | 10+ | 社群參與信號 |
| awesome-mcp-servers 收錄 | ✅ | MCP 生態系曝光 |

### 長期健康指標

- 每月至少 1 個 external contributor PR
- Discussions 有持續活躍的問答
- 使用者在 Show HN / Reddit 留下真實使用回饋

---

## 六、風險評估（業務視角）

| 風險 | 可能性 | 影響 | 緩解策略 |
|------|--------|------|----------|
| 競品快速複製 MCP 整合 | 中 | 中 | 先發優勢 + 持續維護 v2 功能 |
| Reddit / HN API 政策變動 | 低 | 高 | ArXiv 作為備援；GitHub API 穩定 |
| 無人維護後社群流失 | 中 | 高 | 明確標示維護狀態；邀請 contributor |
| 資安問題（API Key 外洩） | 低 | 高 | `.env.example` 已安全；加 security policy |

---

*本文件由 PM / 業務 / 工程協作產出，作為 GitHub 開源發佈的執行依據。*
