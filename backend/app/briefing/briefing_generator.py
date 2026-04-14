"""BriefingGenerator: turns a daily digest report into a developer briefing via Groq."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_BRIEFING_PROMPT = """\
你是一位資深 AI 工程師的技術助理。

⚠️ 核心規則：你**只能使用下方「今日新聞彙整」中出現的文章**。
不得自行補充、引用、或創造任何未在彙整中出現的工具、公司、模型或文章。
若某維度在彙整中找不到對應文章，**必須完全省略該維度區塊**（不輸出標題也不輸出內容）。

以下是今日 AI 新聞彙整（已排除學術論文），每篇文章標有類型標籤：
  [討論] = 工程師分享實戰心得或具體問題
  [實測] = 包含 benchmark、比較或實測數據
  [工具] = 新開源工具或框架
  [社群] = Reddit 討論但無明確分類
  [新聞] = 公司動向、模型釋出等

請依照以下四個維度生成技術簡報，每個維度固定使用條列格式（bullet points）。

選文準則（依優先序）：
1. [討論] 和 [實測] 必須優先選入 — 它們描述具體問題與解法，比工具公告有更高閱讀價值
2. 有具體技術細節的優先（說出方法名稱、數字、或讓人意外的發現）
3. 同等條件下選 score 或 ▲ votes 較高的
4. 每篇文章只能出現在一個維度，選最主要的歸類

描述格式（每條 bullet）：
- **[文章標題關鍵字]** — 說出具體技術方法或發現，再說為什麼值得工程師點進去

禁止：
- 禁止使用「可以幫助開發者...」「展示了...多樣性」「具有重要意義」「值得注意」等空洞結尾
- 禁止引用任何未在今日彙整中出現的文章或工具

---

## 技術模式與架構
（Agent 設計、記憶管理、多代理協作、context window 管理等架構層面）
每個維度 2–4 條。若彙整中無對應文章，省略此區塊。

## 實踐技巧與工具用法
（prompt 工程、claude.md 寫法、MCP server 使用、agentic workflow 等可直接套用的技巧）
若彙整中無對應文章，省略此區塊。

## 開源動態
（值得追蹤的新開源工具或重要版本更新，優先選有設計亮點的）
若彙整中無對應文章，省略此區塊。

## 產業動態
（重要模型釋出、公司動向、政策影響等宏觀資訊）
若彙整中無 [新聞] 類文章，**省略此整個區塊**。

---

格式：繁體中文 Markdown，總字數不超過 800 字。{user_context_section}

今日新聞彙整：
{report_content}"""

_BRIEFING_RETRY_PROMPT = """\
你是一位資深 AI 工程師的技術助理。
請嚴格使用繁體中文（zh-TW）回應。不得使用越南文、泰文、阿拉伯文或任何其他語言的字元。
所有內容必須為繁體中文和英文（技術術語）的組合，不得有其他語言。

⚠️ 核心規則：只使用下方「今日新聞彙整」中出現的文章。不得引用彙整中未出現的任何工具或公司。
若某維度無對應文章，省略該區塊。

以下是今日 AI 新聞彙整（已排除學術論文），每篇文章標有類型標籤：
  [討論] = 工程師分享實戰心得或具體問題
  [實測] = 包含 benchmark、比較或實測數據
  [工具] = 新開源工具或框架
  [社群] = Reddit 討論但無明確分類
  [新聞] = 公司動向、模型釋出等

請依照以下四個維度生成技術簡報，每個維度固定使用條列格式（bullet points）。

選文準則：
1. [討論] 和 [實測] 必須優先選入
2. 每篇文章只能出現在一個維度

描述格式（每條 bullet）：
- **[文章標題關鍵字]** — 說出具體技術方法或發現，再說為什麼值得工程師點進去

禁止：「可以幫助開發者...」「展示了...多樣性」「具有重要意義」及任何未在彙整中出現的內容

## 技術模式與架構
## 實踐技巧與工具用法
## 開源動態
## 產業動態（若無 [新聞] 類文章則省略）

格式：繁體中文 Markdown，總字數不超過 800 字。{user_context_section}

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
