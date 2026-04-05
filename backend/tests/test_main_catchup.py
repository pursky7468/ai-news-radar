"""Tests for startup multi-day catch-up logic (_get_missing_report_dates)."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.store.news_store import NewsStore
from app.main import _get_missing_report_dates


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_store():
    """Isolated in-memory store for each test."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    yield NewsStore(session=session)
    session.close()
    engine.dispose()


def _insert_report(store, generated_at: datetime):
    store.save_report(content="# Report", post_count=5, model_used="groq")
    # Override generated_at directly on the last inserted report
    report = store.get_latest_report()
    report.generated_at = generated_at.replace(tzinfo=None)  # SQLite stores naive
    store._session.flush()


# ---------------------------------------------------------------------------
# _get_missing_report_dates tests
# ---------------------------------------------------------------------------

def test_missing_dates_calculated_correctly(fresh_store):
    """Stopped for 3 days → 3 missing dates returned."""
    today = datetime.now(timezone.utc).date()
    # Only have a report from 4 days ago
    four_days_ago = datetime.now(timezone.utc) - timedelta(days=4)
    _insert_report(fresh_store, four_days_ago)
    fresh_store.commit()

    with patch("app.main.datetime") as mock_dt:
        # Fix "now" to today at 10:00 UTC (past 08:00 so today is also checked)
        now_fixed = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        mock_dt.now.return_value = now_fixed
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        missing = _get_missing_report_dates(fresh_store, max_days=7)

    # Expect: yesterday, 2 days ago, 3 days ago (+ possibly today)
    assert len(missing) >= 3
    assert today - timedelta(days=1) in missing
    assert today - timedelta(days=2) in missing
    assert today - timedelta(days=3) in missing


def test_existing_report_date_not_included(fresh_store):
    """A date that already has a report should not be in missing list."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _insert_report(fresh_store, yesterday)
    fresh_store.commit()

    with patch("app.main.datetime") as mock_dt:
        now_fixed = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        mock_dt.now.return_value = now_fixed
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        missing = _get_missing_report_dates(fresh_store, max_days=3)

    assert yesterday.date() not in missing


def test_catchup_respects_max_days_limit(fresh_store):
    """max_days=3 should only look back 3 days regardless of how long ago last report was."""
    ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
    _insert_report(fresh_store, ten_days_ago)
    fresh_store.commit()

    with patch("app.main.datetime") as mock_dt:
        now_fixed = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        mock_dt.now.return_value = now_fixed
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        missing = _get_missing_report_dates(fresh_store, max_days=3)

    today = now_fixed.date()
    # Only dates within the last 3 days (+ today if past 08:00) should be included
    for d in missing:
        assert d >= today - timedelta(days=3)


def test_today_skipped_before_scheduled_time(fresh_store):
    """Today should NOT be included if current UTC time is before 08:00."""
    today = datetime.now(timezone.utc).date()

    with patch("app.main.datetime") as mock_dt:
        # Fix "now" to 07:00 UTC (before scheduled time)
        now_fixed = datetime.now(timezone.utc).replace(
            year=today.year, month=today.month, day=today.day,
            hour=7, minute=0, second=0, microsecond=0
        )
        mock_dt.now.return_value = now_fixed
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        missing = _get_missing_report_dates(fresh_store, max_days=7)

    assert today not in missing


def test_today_included_after_scheduled_time(fresh_store):
    """Today should be included if current UTC time is >= 08:00 and no report exists."""
    today = datetime.now(timezone.utc).date()

    with patch("app.main.datetime") as mock_dt:
        # Fix "now" to 09:00 UTC (after scheduled time)
        now_fixed = datetime.now(timezone.utc).replace(
            year=today.year, month=today.month, day=today.day,
            hour=9, minute=0, second=0, microsecond=0
        )
        mock_dt.now.return_value = now_fixed
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        missing = _get_missing_report_dates(fresh_store, max_days=7)

    assert today in missing


def test_no_posts_in_window_skips_run():
    """_catchup_digest should skip notifier.run() when there are no posts in the window."""
    from app.main import _catchup_digest

    mock_store = MagicMock()
    mock_store.get_reports.return_value = []
    mock_store.get_unsent_relevant_posts.return_value = []  # no posts available

    mock_notifier = MagicMock()
    mock_session = MagicMock()

    with patch("app.main._get_missing_report_dates") as mock_missing, \
         patch("app.api.deps._SessionLocal", return_value=mock_session), \
         patch("app.store.news_store.NewsStore", return_value=mock_store), \
         patch("app.notifier.digest_notifier.DigestNotifier", return_value=mock_notifier), \
         patch("app.config.settings") as mock_settings:

        mock_settings.catchup_max_days = 7
        mock_settings.digest_lookback_hours = 48
        mock_settings.smtp_config = None
        mock_settings.digest_webhook_url = None
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_model = "gemini-2.0-flash"
        mock_settings.groq_api_key = ""
        mock_settings.groq_model = "llama-3.3-70b-versatile"
        mock_settings.briefings_output_dir = None

        today = datetime.now(timezone.utc).date()
        mock_missing.return_value = [today - timedelta(days=1)]

        _catchup_digest()

    # notifier.run should NOT have been called since no posts are available
    mock_notifier.run.assert_not_called()
