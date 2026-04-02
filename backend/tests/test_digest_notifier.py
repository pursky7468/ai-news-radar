"""Tests for DigestNotifier — TDD Red/Green cycle."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.notifier.digest_notifier import DigestNotifier


def _insert_relevant_post(news_store, external_id: str, score: float = 8.0,
                          source: str = "hackernews"):
    news_store.upsert_post({
        "source": source,
        "external_id": external_id,
        "author_handle": "researcher",
        "content": f"AI agent post #{external_id}",
        "url": f"https://news.ycombinator.com/item?id={external_id}",
        "posted_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "relevance_score": score,
        "is_relevant": True,
        "digest_sent": False,
    })


@pytest.fixture
def notifier(news_store):
    return DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        top_n=5,
    )


# ---------------------------------------------------------------------------
# generate_digest
# ---------------------------------------------------------------------------

def test_generate_digest_returns_top_n_unsent(news_store, notifier):
    for i in range(10):
        _insert_relevant_post(news_store, f"p{i}", score=float(i))
    posts = notifier.generate_digest()
    assert len(posts) == 5
    scores = [p.relevance_score for p in posts]
    assert scores == sorted(scores, reverse=True)


def test_generate_digest_empty_when_no_posts(notifier):
    posts = notifier.generate_digest()
    assert posts == []


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def test_send_email_marks_posts_sent_on_success(news_store):
    _insert_relevant_post(news_store, "pe1")
    smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "user",
        "password": "pass",
        "from": "from@example.com",
        "to": "to@example.com",
    }
    notifier = DigestNotifier(news_store=news_store, smtp_config=smtp_config, webhook_url=None)
    posts = notifier.generate_digest()
    with patch("app.notifier.digest_notifier.smtplib") as mock_smtp:
        mock_smtp_instance = MagicMock()
        mock_smtp.SMTP.return_value.__enter__.return_value = mock_smtp_instance
        success = notifier.send_email(posts)
    assert success is True
    refreshed = news_store.get_unsent_relevant_posts()
    assert len(refreshed) == 0  # all marked sent


def test_send_email_does_not_mark_sent_on_failure(news_store):
    _insert_relevant_post(news_store, "pe2")
    smtp_config = {
        "host": "smtp.fail.com",
        "port": 587,
        "user": "user",
        "password": "pass",
        "from": "from@example.com",
        "to": "to@example.com",
    }
    notifier = DigestNotifier(news_store=news_store, smtp_config=smtp_config, webhook_url=None)
    posts = notifier.generate_digest()
    with patch("app.notifier.digest_notifier.smtplib") as mock_smtp:
        mock_smtp.SMTP.return_value.__enter__.side_effect = Exception("SMTP error")
        success = notifier.send_email(posts)
    assert success is False
    remaining = news_store.get_unsent_relevant_posts()
    assert len(remaining) == 1  # NOT marked sent


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

def test_send_webhook_posts_json_payload(news_store):
    _insert_relevant_post(news_store, "pw1")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url="https://hooks.example.com/abc",
    )
    posts = notifier.generate_digest()
    with patch("app.notifier.digest_notifier.httpx") as mock_httpx:
        mock_httpx.post.return_value = MagicMock(status_code=200)
        success = notifier.send_webhook(posts)
    assert success is True
    mock_httpx.post.assert_called_once()
    call_kwargs = mock_httpx.post.call_args
    assert "json" in call_kwargs.kwargs or len(call_kwargs.args) > 1


def test_send_webhook_skipped_when_not_configured(news_store):
    _insert_relevant_post(news_store, "pw2")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
    )
    posts = notifier.generate_digest()
    success = notifier.send_webhook(posts)
    # returns True (no-op) when not configured
    assert success is True


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def test_run_returns_correct_summary(news_store):
    for i in range(3):
        _insert_relevant_post(news_store, f"run_p{i}")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
    )
    summary = notifier.run()
    assert summary["posts_included"] == 3
    assert summary["email_sent"] is False
    assert summary["webhook_sent"] is False


def test_run_does_not_mark_sent_when_any_channel_fails(news_store):
    _insert_relevant_post(news_store, "fail_p1")
    smtp_config = {
        "host": "smtp.fail.com", "port": 587,
        "user": "u", "password": "p",
        "from": "f@e.com", "to": "t@e.com",
    }
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=smtp_config,
        webhook_url="https://hooks.example.com/fail",
    )
    with (
        patch("app.notifier.digest_notifier.smtplib") as mock_smtp,
        patch("app.notifier.digest_notifier.httpx") as mock_httpx,
    ):
        mock_smtp.SMTP.return_value.__enter__.side_effect = Exception("fail")
        mock_httpx.post.return_value = MagicMock(status_code=200)
        summary = notifier.run()

    # email failed → posts NOT marked sent
    remaining = news_store.get_unsent_relevant_posts()
    assert len(remaining) == 1
    assert summary["email_sent"] is False
