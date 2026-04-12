"""BriefingGenerator: turns a daily digest report into a developer briefing via Groq."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_BRIEFING_PROMPT = """\
你是一位資深 AI 工程師的技術助理。
以下是今日 AI 新聞彙整（已排除學術論文），請生成一份開發者技術簡報。

請依照以下四個維度組織內容，每個維度 2–4 條重點，每條 2–3 句說明。
說明必須指出「為什麼值得注意」，不只轉述標題。
若某維度今日無相關內容，則省略該區塊。

## 技術模式與架構
（Agent 設計、記憶管理、多代理協作、context window 管理等架構層面的進展）

## 實踐技巧與工具用法
（prompt 工程、claude.md 寫法、MCP server 使用、vibe coding、AI 協作工作流程等實踐層面的技巧）

## 開源動態
（值得關注的新開源工具、框架釋出、重要版本更新）

## 產業動態
（重要模型釋出、公司動向、政策影響等宏觀資訊）

格式：繁體中文 Markdown，總字數不超過 700 字。{user_context_section}

今日新聞彙整：
{report_content}"""

_BRIEFING_RETRY_PROMPT = """\
你是一位資深 AI 工程師的技術助理。
請嚴格使用繁體中文（zh-TW）回應。不得使用越南文、泰文、阿拉伯文或任何其他語言的字元。
所有內容必須為繁體中文和英文（技術術語）的組合，不得有其他語言。

以下是今日 AI 新聞彙整（已排除學術論文），請生成一份開發者技術簡報。

請依照以下四個維度組織內容，每個維度 2–4 條重點，每條 2–3 句說明。
說明必須指出「為什麼值得注意」，不只轉述標題。
若某維度今日無相關內容，則省略該區塊。

## 技術模式與架構
（Agent 設計、記憶管理、多代理協作、context window 管理等架構層面的進展）

## 實踐技巧與工具用法
（prompt 工程、claude.md 寫法、MCP server 使用、vibe coding、AI 協作工作流程等實踐層面的技巧）

## 開源動態
（值得關注的新開源工具、框架釋出、重要版本更新）

## 產業動態
（重要模型釋出、公司動向、政策影響等宏觀資訊）

格式：繁體中文 Markdown，總字數不超過 700 字。{user_context_section}

今日新聞彙整：
{report_content}"""

_USER_CONTEXT_TEMPLATE = "\n\n使用者當前工作 context：{user_context}"

# Unicode ranges that are acceptable in the output
_ALLOWED_UNICODE_RANGES = [
    (0x0000, 0x007F),   # Basic Latin (ASCII — covers English tech terms)
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms (CJK punctuation variants)
    (0x2000, 0x206F),   # General Punctuation (e.g. —, …)
    (0x0020, 0x0020),   # Space (already in Basic Latin, listed for clarity)
]


def _validate_language(text: str) -> bool:
    """Return True if text contains only allowed Unicode blocks (CJK + Basic Latin).

    Triggers on unexpected blocks such as Vietnamese Latin extensions,
    Arabic, Thai, Cyrillic, etc.
    """
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _ALLOWED_UNICODE_RANGES):
            continue
        # Common safe punctuation not already covered
        if cp in (0x00B7, 0x00D7, 0x00F7):  # middle dot, ×, ÷
            continue
        if 0x2100 <= cp <= 0x214F:  # Letterlike Symbols (℃, ™, etc.)
            continue
        logger.debug("Language validation failed at char U+%04X (%s)", cp, ch)
        return False
    return True


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

        result = self._groq_request(client, _BRIEFING_PROMPT, report_content, user_ctx)

        if not _validate_language(result):
            logger.warning("BriefingGenerator: language validation failed, retrying with stricter prompt.")
            result = self._groq_request(client, _BRIEFING_RETRY_PROMPT, report_content, user_ctx)
            if not _validate_language(result):
                logger.warning("BriefingGenerator: retry also failed language validation — adding warning header.")
                result = "⚠️ [語言品質警告：部分內容可能包含非預期語言字元]\n\n" + result

        return result

    def _groq_request(self, client, prompt_template: str, report_content: str, user_ctx: str) -> str:
        prompt = prompt_template.format(
            report_content=report_content,
            user_context_section=user_ctx,
        )
        resp = client.chat.completions.create(
            model=self._groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
