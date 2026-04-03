"""GroqClient: wraps Groq SDK for per-post zh-TW summarization."""
from __future__ import annotations

import logging
import time

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
請用繁體中文在100字以內摘要以下AI相關內容的重點：
來源：{source}
內容：{content}
請直接回答摘要，不需要額外說明。"""

_FALLBACK_LEN = 50


class GroqClient:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def summarize_post(self, post) -> str:
        """Return zh-TW summary (≤100 chars). Retries once on 429; falls back to excerpt."""
        content = (getattr(post, "content", None) or "")[:500]
        source = getattr(post, "source", "unknown")
        prompt = _PROMPT_TEMPLATE.format(source=source, content=content)

        for attempt in range(2):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
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
