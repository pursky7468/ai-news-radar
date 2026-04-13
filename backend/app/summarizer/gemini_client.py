"""GeminiClient: wraps google-generativeai SDK for per-post zh-TW summarization."""
from __future__ import annotations

import logging
import time

import google.generativeai as genai

logger = logging.getLogger(__name__)

_FALLBACK_LEN = 50


def _build_prompt(source: str, content: str) -> str:
    """Return source-aware summarization prompt. Imported from groq_client for DRY."""
    from app.summarizer.groq_client import _build_prompt as _bp
    return _bp(source, content)


_CONTENT_LIMIT = 1500


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._model_name = model

    def summarize_post(self, post) -> str:
        """Return zh-TW summary with technical insight. Retries once on 429; falls back to excerpt."""
        content = (getattr(post, "content", None) or "")[:_CONTENT_LIMIT]
        source = getattr(post, "source", "unknown")
        prompt = _build_prompt(source, content)

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
