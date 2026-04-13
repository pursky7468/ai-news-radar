"""GroqClient: wraps Groq SDK for per-post zh-TW summarization."""
from __future__ import annotations

import logging
import time

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

# Source-aware prompts: Reddit discussions need different treatment than GitHub repos
_PROMPT_REDDIT = """\
以下是一篇 Reddit 討論貼文，請用繁體中文生成技術摘要（100–150字）。

摘要必須涵蓋三個面向：
1. 作者遇到的具體問題或分享的核心內容（一句話，說清楚場景）
2. 作者採用的具體技術方法（說出方法名稱或步驟，不要泛稱「AI 方案」）
3. 為何值得工程師點進去看（找出讓人意外或特別實用的點）

禁止使用的結尾：「可以幫助開發者...」「具有重要意義」「展示了...多樣性」

內容：
{content}

請直接輸出摘要，不需要標題或額外說明。"""

_PROMPT_GITHUB = """\
以下是一個 GitHub 專案描述，請用繁體中文生成技術摘要（80–120字）。

摘要必須涵蓋：
1. 這個工具解決的核心問題（說出具體痛點，不是泛稱「AI 應用程式問題」）
2. 和現有方案不同的設計決策（說出技術差異，例如：不用 vector DB 而用 graph、不依賴 sandbox 等）
3. 適合什麼情境使用（一句話）

禁止使用的結尾：「可以幫助開發者...」「具有重要意義」

內容：
{content}

請直接輸出摘要，不需要標題或額外說明。"""

_PROMPT_DEFAULT = """\
以下是一則 AI 相關內容（來源：{source}），請用繁體中文生成技術摘要（80–120字）。

摘要必須說明：
1. 核心內容是什麼（具體，不泛稱）
2. 技術上有什麼值得注意的點（方法、數字、設計決策）
3. 為何值得關注 AI 領域的工程師點進去看

禁止使用的結尾：「可以幫助開發者...」「具有重要意義」

內容：
{content}

請直接輸出摘要，不需要標題或額外說明。"""

_CONTENT_LIMIT = 1500  # increased from 500 — Reddit posts can be 2000 chars
_FALLBACK_LEN = 50


def _build_prompt(source: str, content: str) -> str:
    if source == "reddit":
        return _PROMPT_REDDIT.format(content=content)
    if source == "github":
        return _PROMPT_GITHUB.format(content=content)
    return _PROMPT_DEFAULT.format(source=source, content=content)


class GroqClient:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def summarize_post(self, post) -> str:
        """Return zh-TW summary with technical insight. Retries once on 429; falls back to excerpt."""
        content = (getattr(post, "content", None) or "")[:_CONTENT_LIMIT]
        source = getattr(post, "source", "unknown")
        prompt = _build_prompt(source, content)

        for attempt in range(2):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                )
                return resp.choices[0].message.content.strip()
            except RateLimitError as exc:
                if attempt == 0:
                    logger.warning("Groq 429 rate limit — waiting 60s before retry")
                    time.sleep(60)
                    continue
                logger.warning("Groq summarize_post failed (attempt %d): %s", attempt + 1, exc)
                break
            except Exception as exc:
                logger.warning("Groq summarize_post failed (attempt %d): %s", attempt + 1, exc)
                break

        fallback = (getattr(post, "content", None) or "")[:_FALLBACK_LEN]
        return fallback + "…" if fallback else ""
