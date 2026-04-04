"""Tests for DigestNotifier — TDD Red/Green cycle."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

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
        "posted_at": datetime.now(timezone.utc) - timedelta(hours=1),
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

def test_send_email_returns_true_on_success(news_store):
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
        mock_smtp.SMTP.return_value.__enter__.return_value = MagicMock()
        success = notifier.send_email(posts)
    assert success is True


def test_send_email_returns_false_on_failure(news_store):
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


def test_send_webhook_payload_includes_summary_zh(news_store):
    _insert_relevant_post(news_store, "pw_zh")
    news_store.update_post_summary(
        news_store.query_posts()[0].id, "AI 代理人新進展"
    )
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url="https://hooks.example.com/abc",
    )
    posts = notifier.generate_digest()
    with patch("app.notifier.digest_notifier.httpx") as mock_httpx:
        mock_httpx.post.return_value = MagicMock(status_code=200)
        notifier.send_webhook(posts)
    payload = mock_httpx.post.call_args.kwargs["json"]
    assert payload["digest"][0]["summary_zh"] == "AI 代理人新進展"
    assert "report_markdown" in payload


def test_send_webhook_skipped_when_not_configured(news_store):
    _insert_relevant_post(news_store, "pw2")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
    )
    posts = notifier.generate_digest()
    success = notifier.send_webhook(posts)
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
    result = notifier.run()
    assert result["posts_included"] == 3
    assert result["email_sent"] is False
    assert result["webhook_sent"] is False


def test_run_marks_sent_when_no_channels_configured(news_store):
    _insert_relevant_post(news_store, "run_mark1")
    notifier = DigestNotifier(news_store=news_store, smtp_config=None, webhook_url=None)
    notifier.run()
    remaining = news_store.get_unsent_relevant_posts()
    assert len(remaining) == 0


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
        result = notifier.run()

    remaining = news_store.get_unsent_relevant_posts()
    assert len(remaining) == 1
    assert result["email_sent"] is False


# ---------------------------------------------------------------------------
# Summarization integration
# ---------------------------------------------------------------------------

def test_run_calls_summarization_when_gemini_key_set(news_store):
    _insert_relevant_post(news_store, "sum_p1")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        gemini_api_key="fake-key",
        gemini_model="gemini-2.0-flash",
    )
    with patch.object(notifier, "_run_summarization", return_value="# 報告") as mock_sum:
        notifier.run()
    mock_sum.assert_called_once()


def test_run_skips_summarization_when_no_gemini_key(news_store):
    _insert_relevant_post(news_store, "sum_p2")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        gemini_api_key="",
    )
    with patch.object(notifier, "_run_summarization") as mock_sum:
        notifier.run()
    mock_sum.assert_not_called()


def test_generate_digest_with_lookback_excludes_old_posts(news_store):
    now = datetime.now(timezone.utc)
    _insert_relevant_post_at(news_store, "new_post", now - timedelta(hours=24))
    _insert_relevant_post_at(news_store, "old_post", now - timedelta(hours=72))
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        lookback_hours=48,
    )
    posts = notifier.generate_digest()
    ids = [p.external_id for p in posts]
    assert "new_post" in ids
    assert "old_post" not in ids


def test_generate_digest_lookback_zero_includes_all(news_store):
    now = datetime.now(timezone.utc)
    _insert_relevant_post_at(news_store, "new_post", now - timedelta(hours=24))
    _insert_relevant_post_at(news_store, "old_post", now - timedelta(hours=720))
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        lookback_hours=0,
    )
    posts = notifier.generate_digest()
    ids = [p.external_id for p in posts]
    assert "new_post" in ids
    assert "old_post" in ids


def _insert_relevant_post_at(news_store, external_id: str, posted_at: datetime):
    news_store.upsert_post({
        "source": "hackernews",
        "external_id": external_id,
        "author_handle": "researcher",
        "content": f"AI post #{external_id}",
        "url": f"https://news.ycombinator.com/item?id={external_id}",
        "posted_at": posted_at,
        "relevance_score": 8.0,
        "is_relevant": True,
        "digest_sent": False,
    })
