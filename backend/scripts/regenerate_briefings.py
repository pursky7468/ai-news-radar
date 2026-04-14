"""
Regenerate past briefings using the current prompt and report format.

Queries posts by posted_at date range for each day, assembles a report
with type labels (Phase C), and re-generates the briefing with the
improved anti-hallucination prompt.

Usage:
    python scripts/regenerate_briefings.py                  # last 7 days
    python scripts/regenerate_briefings.py --days 14        # last 14 days
    python scripts/regenerate_briefings.py --date 2026-04-12  # single date
    python scripts/regenerate_briefings.py --force          # overwrite existing files
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.store.news_store import NewsStore
from app.summarizer.summary_generator import SummaryGenerator
from app.briefing.briefing_generator import BriefingGenerator


def _get_posts_for_date(store: NewsStore, target_date: datetime, lookback_hours: int = 48):
    """Query relevant posts with posted_at within [target_date - lookback, target_date]."""
    since = target_date - timedelta(hours=lookback_hours)
    posts = store.get_unsent_relevant_posts(limit=200, since=since)
    # Filter to posted_at <= target_date end-of-day
    cutoff = target_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    return [
        p for p in posts
        if (p.posted_at.replace(tzinfo=timezone.utc) if p.posted_at.tzinfo is None else p.posted_at) <= cutoff
    ]


def regenerate_for_date(
    session: Session,
    target_date: datetime,
    output_dir: Path,
    force: bool = False,
    groq_api_key: str = "",
    groq_model: str = "llama-3.3-70b-versatile",
    user_context: str = "",
    lookback_hours: int = 48,
) -> bool:
    date_str = target_date.strftime("%Y-%m-%d")
    out_path = output_dir / f"{date_str}.md"

    if out_path.exists() and not force:
        print(f"  [{date_str}] skip — already exists (use --force to overwrite)")
        return False

    store = NewsStore(session)

    # Get posts for this date
    posts = _get_posts_for_date(store, target_date, lookback_hours)
    if not posts:
        print(f"  [{date_str}] skip — no relevant posts found")
        return False

    # Sort by relevance_score DESC, take top 20
    posts.sort(key=lambda p: (p.relevance_score or 0), reverse=True)
    posts = posts[:20]

    print(f"  [{date_str}] {len(posts)} posts -> assembling report...")

    # Assemble report with Phase C type labels
    from app.summarizer.summary_generator import SummaryGenerator as SG
    from app.summarizer.gemini_client import GeminiClient

    # We don't re-summarize here — use existing summary_zh as-is
    # Just assemble the report
    gemini_client = GeminiClient(api_key=settings.gemini_api_key or "", model=settings.gemini_model)
    gen = SG(gemini_client=gemini_client, store=store)
    report = gen.assemble_report(posts, date=date_str)

    if not report.strip():
        print(f"  [{date_str}] skip — empty report")
        return False

    # Build highlight section if available (top 3 only)
    highlight_posts = None
    if settings.FEATURES.get("highlight_scorer"):
        from app.briefing.highlight_scorer import get_top_highlights
        non_arxiv = [p for p in posts if (p.source or "") != "arxiv"]
        highlight_posts = get_top_highlights(non_arxiv, n=3, reference_time=target_date)

    highlight_weights = None
    if hasattr(settings, "highlight_weights"):
        highlight_weights = settings.highlight_weights

    # Generate briefing with new prompt
    generator = BriefingGenerator(
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        output_dir=output_dir,
        user_context=user_context,
        highlight_posts=highlight_posts,
        highlight_weights=highlight_weights,
    )

    # Temporarily allow overwrite by deleting file if force
    if out_path.exists() and force:
        out_path.unlink()

    result = generator.generate(report, date=target_date)
    if result:
        print(f"  [{date_str}] OK saved -> {result}")
        return True
    else:
        print(f"  [{date_str}] FAIL generation failed")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate past briefings with improved prompt.")
    parser.add_argument("--days", type=int, default=7, help="Number of past days to regenerate (default: 7)")
    parser.add_argument("--date", default=None, help="Single date to regenerate (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing briefing files")
    parser.add_argument("--lookback-hours", type=int, default=48, help="Hours of posts to include per day")
    args = parser.parse_args()

    groq_api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key:
        print("Error: GROQ_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    groq_model = settings.groq_model or "llama-3.3-70b-versatile"
    user_context = settings.user_context or ""
    output_dir = Path(settings.briefings_output_dir_resolved)

    engine = create_engine(settings.database_url)

    if args.date:
        dates = [datetime.strptime(args.date, "%Y-%m-%d").replace(
            hour=20, minute=0, tzinfo=timezone.utc)]
    else:
        today = datetime.now(timezone.utc).replace(hour=20, minute=0, second=0, microsecond=0)
        dates = [today - timedelta(days=i) for i in range(1, args.days + 1)]

    print(f"Regenerating {len(dates)} briefing(s)...")
    print(f"  Output: {output_dir}")
    print(f"  Model: {groq_model}")
    print(f"  Force: {args.force}")
    print()

    success = 0
    for target_date in reversed(dates):  # oldest first
        with Session(engine) as session:
            ok = regenerate_for_date(
                session=session,
                target_date=target_date,
                output_dir=output_dir,
                force=args.force,
                groq_api_key=groq_api_key,
                groq_model=groq_model,
                user_context=user_context,
                lookback_hours=args.lookback_hours,
            )
            if ok:
                success += 1
                time.sleep(3)  # Rate limit between Groq calls

    print(f"\nDone: {success}/{len(dates)} briefings regenerated.")


if __name__ == "__main__":
    main()
