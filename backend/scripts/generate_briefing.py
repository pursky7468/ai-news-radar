"""
Phase 15a: Daily Markdown Briefing Script

Fetches today's AI news report from the local API, sends it to Groq for
developer-focused analysis, and saves the output to briefings/YYYY-MM-DD.md.

Usage:
    python scripts/generate_briefing.py [--date YYYY-MM-DD] [--api-url URL]

The API_BASE_URL defaults to http://localhost:8000.
GROQ_API_KEY must be set in the environment or .env file.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from backend/ or repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

_BRIEFING_PROMPT = """\
你是一位資深 AI 工程師的技術助理。
以下是今日 AI 新聞彙整，請生成一份開發者技術簡報，包含：
1. 3–5 個今日重點技術趨勢（各 2–3 句說明）
2. 對軟體開發者最值得關注的技術或工具
3. 1–2 個具體行動建議

格式：繁體中文 Markdown，不超過 600 字。

今日新聞彙整：
{report_content}"""


def _fetch_report(api_base: str) -> tuple[str, str]:
    """Return (report_markdown, report_date_str). Raises on failure."""
    resp = httpx.get(f"{api_base}/api/summary/latest", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    content: str = data.get("content", "")
    generated_at: str = data.get("generated_at", "")
    if not content:
        raise ValueError("Report content is empty — run digest first.")
    # Extract date string
    if generated_at:
        date_str = generated_at[:10]
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return content, date_str


def _generate_briefing(report_content: str, groq_api_key: str, groq_model: str) -> str:
    """Send report to Groq and return the briefing Markdown."""
    from groq import Groq

    client = Groq(api_key=groq_api_key)
    prompt = _BRIEFING_PROMPT.format(report_content=report_content)
    resp = client.chat.completions.create(
        model=groq_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )
    return resp.choices[0].message.content.strip()


def _save_briefing(briefing: str, date_str: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{date_str}.md"
    out_path.write_text(briefing, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a daily AI tech briefing.")
    parser.add_argument("--api-url", default="http://localhost:8000",
                        help="Base URL of the backend API (default: http://localhost:8000)")
    parser.add_argument("--date", default=None,
                        help="Override date label for output file (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default=None,
                        help="Directory to save briefings (default: <repo_root>/briefings)")
    args = parser.parse_args()

    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not groq_api_key:
        print("Error: GROQ_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching latest report from {args.api_url}…")
    report_content, date_str = _fetch_report(args.api_url)

    if args.date:
        date_str = args.date

    print(f"Report date: {date_str}  ({len(report_content)} chars)")
    print(f"Sending to Groq ({groq_model}) for analysis…")

    briefing = _generate_briefing(report_content, groq_api_key, groq_model)

    # Default output dir: <repo_root>/briefings
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent.parent / "briefings"

    out_path = _save_briefing(briefing, date_str, output_dir)
    print(f"Briefing saved → {out_path}")


if __name__ == "__main__":
    main()
