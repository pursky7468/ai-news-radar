"""Tests for FetchPipeline and scheduler — TDD Red/Green cycle."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.fetch_pipeline import FetchPipeline


@pytest.fixture
def mock_fetcher():
    m = MagicMock()
    m.fetch.return_value = [
        {
            "source": "hackernews",
            "external_id": "t1",
            "author_handle": "user_a",
            "content": "AI agent orchestration using tool calling",
            "url": "https://news.ycombinator.com/item?id=t1",
            "posted_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
    ]
    return m


@pytest.fixture
def mock_scorer():
    m = MagicMock()
    m.score_post.return_value = {
        "relevance_score": 8.5,
        "labels": ["ai-agent"],
        "is_relevant": True,
    }
    return m


@pytest.fixture
def pipeline(news_store, mock_fetcher, mock_scorer):
    return FetchPipeline(
        news_store=news_store,
        fetcher=mock_fetcher,
        scorer=mock_scorer,
    )


def test_pipeline_runs_fetch_then_score_then_store(pipeline, news_store, mock_fetcher, mock_scorer):
    pipeline.run()
    mock_fetcher.fetch.assert_called_once()
    mock_scorer.score_post.assert_called_once()
    posts = news_store.query_posts()
    assert len(posts) == 1
    assert posts[0].relevance_score == 8.5


def test_pipeline_logs_counts(pipeline, caplog):
    import logging
    with caplog.at_level(logging.INFO):
        pipeline.run()
    assert any("fetched" in r.message.lower() or "stored" in r.message.lower() for r in caplog.records)


def test_pipeline_handles_empty_fetch(news_store, mock_scorer):
    fetcher = MagicMock()
    fetcher.fetch.return_value = []
    pl = FetchPipeline(
        news_store=news_store,
        fetcher=fetcher,
        scorer=mock_scorer,
    )
    pl.run()  # should not raise
    assert news_store.query_posts() == []


def test_scheduler_registers_two_jobs():
    from app.pipeline.scheduler import build_scheduler
    sched = build_scheduler(
        fetch_interval_minutes=15,
        digest_cron="0 8 * * *",
        fetch_pipeline=MagicMock(),
        digest_notifier=MagicMock(),
    )
    jobs = sched.get_jobs()
    assert len(jobs) == 2
