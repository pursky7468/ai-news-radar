"""Manual script to generate the weekly AI trend briefing.

Usage:
    python scripts/generate_weekly_briefing.py

Generates briefings/weekly/YYYY-WNN.md for the current ISO week.
Overwrites any existing file for the same week.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from backend/
_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")
load_dotenv(_BACKEND.parent / ".env", override=False)

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.briefing.weekly_briefing_generator import WeeklyBriefingGenerator
from app.config import settings
from app.models import Base
from app.store.news_store import NewsStore

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def main() -> None:
    if not settings.groq_api_key:
        print("ERROR: GROQ_API_KEY is not set.")
        sys.exit(1)

    db = Session()
    try:
        store = NewsStore(session=db)
        since = datetime.now(timezone.utc) - timedelta(days=7)
        posts = store.query_posts(is_relevant=True, since=since, per_page=200, sort="score_desc")
        print(f"Found {len(posts)} relevant posts in the last 7 days.")

        output_dir = Path(settings.briefings_output_dir or "briefings") / "weekly"
        generator = WeeklyBriefingGenerator(
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
            output_dir=output_dir,
        )
        path = generator.generate(posts)
        if path:
            print(f"Weekly briefing saved → {path}")
        else:
            print("Weekly briefing was not generated (too few posts or API error).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
