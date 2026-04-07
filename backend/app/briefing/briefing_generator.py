"""BriefingGenerator: turns a daily digest report into a developer briefing via Groq."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_BRIEFING_PROMPT = """\
你是一位資深 AI 工程師的技術助理。
以下是今日 AI 新聞彙整，請生成一份開發者技術簡報，包含：
1. 3–5 個今日重點技術趨勢（各 2–3 句說明）
2. 對軟體開發者最值得關注的技術或工具
3. 1–2 個具體行動建議

格式：繁體中文 Markdown，不超過 600 字。{user_context_section}

今日新聞彙整：
{report_content}"""

_USER_CONTEXT_TEMPLATE = "\n\n使用者當前工作 context：{user_context}"


class BriefingGenerator:
    """Generate a daily Markdown briefing from the latest report content."""

    def __init__(
        self,
        groq_api_key: str,
        groq_model: str = "llama-3.3-70b-versatile",
        output_dir: str | Path = "briefings",
        user_context: str = "",
        highlight_posts=None,
        highlight_weights: dict | None = None,
    ) -> None:
        self._groq_api_key = groq_api_key
        self._groq_model = groq_model
        self._output_dir = Path(output_dir)
        self._user_context = user_context
        self._highlight_posts = highlight_posts  # list[Post] or None
        self._highlight_weights = highlight_weights

    def generate(self, report_content: str, date: datetime | None = None) -> Path | None:
        """
        Analyse *report_content* with Groq and save to
        <output_dir>/YYYY-MM-DD.md.  Returns the saved path, or None on failure.
        """
        if not self._groq_api_key:
            logger.debug("BriefingGenerator: no GROQ_API_KEY, skipping.")
            return None
        if not report_content:
            logger.warning("BriefingGenerator: report content is empty, skipping.")
            return None

        date = date or datetime.now(timezone.utc)
        date_str = date.strftime("%Y-%m-%d")

        try:
            briefing = self._call_groq(report_content)
        except Exception as exc:
            logger.error("BriefingGenerator: Groq call failed: %s", exc)
            return None

        # Prepend highlight section if provided
        if self._highlight_posts:
            try:
                from app.briefing.highlight_scorer import format_highlight_section
                highlight_md = format_highlight_section(
                    self._highlight_posts,
                    reference_time=date,
                    weights=self._highlight_weights,
                )
                briefing = highlight_md + briefing
            except Exception as exc:
                logger.warning("BriefingGenerator: highlight section failed: %s", exc)

        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._output_dir / f"{date_str}.md"
        if out_path.exists():
            logger.info("Briefing already exists, skipping → %s", out_path)
            return out_path
        out_path.write_text(briefing, encoding="utf-8")
        logger.info("Briefing saved → %s", out_path)
        return out_path

    def _call_groq(self, report_content: str) -> str:
        from groq import Groq

        user_ctx = ""
        if self._user_context:
            user_ctx = _USER_CONTEXT_TEMPLATE.format(user_context=self._user_context)

        client = Groq(api_key=self._groq_api_key)
        prompt = _BRIEFING_PROMPT.format(
            report_content=report_content,
            user_context_section=user_ctx,
        )
        resp = client.chat.completions.create(
            model=self._groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
