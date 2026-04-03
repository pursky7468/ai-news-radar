"""GeminiClient: wraps google-generativeai SDK for per-post zh-TW summarization."""
from __future__ import annotations

import logging
import time

import google.generativeai as genai

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
請用繁體中文在100字以內摘要以下AI相關內容的重點：
來源：{source}
內容：{content}
請直接回答摘要，不需要額外說明。"""

_FALLBACK_LEN = 50


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._model_name = model

    def summarize_post(self, post) -> str:
        """Return zh-TW summary (≤100 chars). Retries once on 429; falls back to excerpt."""
        content = (getattr(post, "content", None) or "")[:500]
        source = getattr(post, "source", "unknown")
        prompt = _PROMPT_TEMPLATE.format(source=source, content=content)

        for attempt in range(2):
            try:
                resp = self._model.generate_content(prompt)
                return resp.text.strip()
            except Exception as exc:
                if "429" in str(exc) and attempt == 0:
                    logger.warning("Gemini 429 rate limit — waiting 60s before retry")
                    time.sleep(60)
                    continue
                logger.warning("Gemini summarize_post failed (attempt %d): %s", attempt + 1, exc)
                break

        # fallback: untranslated excerpt
        fallback = (getattr(post, "content", None) or "")[:_FALLBACK_LEN]
        return fallback + "…" if fallback else ""
