"""
MCP Server for x-ai-news-researcher (Phase 15b)

Exposes three tools to Claude Desktop / any MCP-compatible agent:
  - search_ai_news      — keyword search, all-time by default
  - get_daily_report    — retrieve a specific day's briefing report
  - get_posts_by_category — posts filtered by label

Usage (standalone):
    python mcp_server.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "ai-news": {
          "command": "python",
          "args": ["<absolute_path>/backend/mcp_server.py"],
          "cwd": "<absolute_path>/backend"
        }
      }
    }

Requires: GROQ_API_KEY (optional) and DATABASE_URL in .env or environment.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Resolve backend package path
_BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env", override=False)

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base
from app.store.news_store import NewsStore

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

_engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


def _store() -> NewsStore:
    return NewsStore(session=_Session())


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("ai-news-researcher")


@mcp.tool()
def search_ai_news(query: str, days: int = 0, limit: int = 10) -> str:
    """
    Search AI news posts by keyword.

    Args:
        query: Search keyword (e.g. "MCP", "streaming LLM", "AutoGen")
        days:  Only return posts from the last N days. 0 = all time (default).
        limit: Maximum number of posts to return (default 10, max 50).

    Returns:
        Markdown list of matching posts with title, source, URL, score, and summary.
    """
    limit = min(limit, 50)
    since = None
    if days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)

    store = _store()
    posts = store.query_posts(
        keyword=query,
        since=since,
        is_relevant=True,
        sort="score_desc",
        per_page=limit,
    )

    if not posts:
        return f"No posts found for query: **{query}**"

    lines = [f"## Search results for: {query}\n"]
    for p in posts:
        date_str = p.posted_at.strftime("%Y-%m-%d") if p.posted_at else "unknown"
        summary = p.summary_zh or p.content[:100]
        labels = ", ".join(p.labels or [])
        lines.append(
            f"### [{p.content[:80]}]({p.url})\n"
            f"- **來源**: {p.source}  **日期**: {date_str}  **分數**: {p.relevance_score:.1f}\n"
            f"- **標籤**: {labels}\n"
            f"- **摘要**: {summary}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def get_daily_report(date: str = "today") -> str:
    """
    Retrieve a daily AI news digest report.

    Args:
        date: Date in YYYY-MM-DD format, or "today" / "yesterday" (default: "today").

    Returns:
        Full Markdown report for that day, or a message if not found.
    """
    now = datetime.now(timezone.utc)

    if date == "today":
        target = now.date()
    elif date == "yesterday":
        target = (now - timedelta(days=1)).date()
    else:
        try:
            target = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return f"Invalid date format: '{date}'. Use YYYY-MM-DD, 'today', or 'yesterday'."

    store = _store()
    reports = store.get_reports(limit=100)

    for report in reports:
        report_date = report.generated_at.date() if report.generated_at else None
        if report_date == target:
            return report.content or f"Report for {target} has no content."

    return f"No report found for {target}. Reports are generated daily at 8:00 AM."


@mcp.tool()
def get_posts_by_category(category: str, days: int = 7, limit: int = 10) -> str:
    """
    Get recent AI news posts filtered by category label.

    Args:
        category: One of "ai-agent", "ai-model", "ai-tool", or "other".
        days:     Look back N days (default 7). Use 0 for all time.
        limit:    Maximum number of posts (default 10, max 50).

    Returns:
        Markdown list of posts in the given category.
    """
    valid_categories = {"ai-agent", "ai-model", "ai-tool", "other"}
    if category not in valid_categories:
        return (
            f"Unknown category: '{category}'. "
            f"Valid options: {', '.join(sorted(valid_categories))}"
        )

    limit = min(limit, 50)
    since = None
    if days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)

    store = _store()
    posts = store.query_posts(
        label=category,
        since=since,
        is_relevant=True,
        sort="score_desc",
        per_page=limit,
    )

    if not posts:
        period = f"last {days} days" if days > 0 else "all time"
        return f"No posts found in category **{category}** ({period})."

    category_labels = {
        "ai-agent": "🤖 AI Agent",
        "ai-model": "🧠 AI 模型",
        "ai-tool": "🛠 AI 工具",
        "other": "📰 其他",
    }
    header = category_labels.get(category, category)
    lines = [f"## {header}\n"]

    for p in posts:
        date_str = p.posted_at.strftime("%Y-%m-%d") if p.posted_at else "unknown"
        summary = p.summary_zh or p.content[:100]
        lines.append(
            f"### [{p.content[:80]}]({p.url})\n"
            f"- **來源**: {p.source}  **日期**: {date_str}  **分數**: {p.relevance_score:.1f}\n"
            f"- **摘要**: {summary}\n"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
