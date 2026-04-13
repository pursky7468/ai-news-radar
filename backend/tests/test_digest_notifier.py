"""Tests for DigestNotifier — TDD Red/Green cycle."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

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


# ---------------------------------------------------------------------------
# reference_time injection (Phase 16)
# ---------------------------------------------------------------------------

def test_run_with_reference_time_uses_correct_window(news_store):
    """generate_digest with reference_time=T should use since = T - lookback_hours."""
    now = datetime.now(timezone.utc)
    ref = now - timedelta(days=2)  # two days ago

    # post inside the ref window (ref - 24h)
    _insert_relevant_post_at(news_store, "in_window", ref - timedelta(hours=24))
    # post outside the ref window (ref - 60h, but inside "real now - 48h" window)
    _insert_relevant_post_at(news_store, "out_of_window", ref - timedelta(hours=60))

    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        lookback_hours=48,
    )
    posts = notifier.generate_digest(reference_time=ref)
    ids = [p.external_id for p in posts]
    assert "in_window" in ids
    assert "out_of_window" not in ids


# ---------------------------------------------------------------------------
# Regression: PendingRollbackError — summarize_batch DB failure must not
# prevent mark_digest_sent from succeeding.
# ---------------------------------------------------------------------------

def test_run_marks_sent_despite_db_error_in_summarize_batch():
    """Regression: DB error in summarize_batch must not poison mark_digest_sent.

    Reproduces the 8 AM cron crash: update_post_summary causes a real
    SQLAlchemy session-level error; without rollback the session enters
    PendingRollbackError state and mark_digest_sent raises.

    Uses a standalone in-memory DB (not the shared transactional fixture)
    so that calling session.rollback() in the fix code does not undo test
    setup data.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession
    from app.models import Base
    from app.store.news_store import NewsStore as _NS

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = OrmSession(engine)
    store = _NS(session=db)

    _insert_relevant_post(store, "reg_pending_rollback")
    db.commit()

    notifier = DigestNotifier(
        news_store=store,
        smtp_config=None,
        webhook_url=None,
        groq_api_key="fake-key",
    )

    def corrupt_session_then_raise(post_id, summary_zh):
        # Execute invalid SQL against the real session to trigger a DB-level
        # error, then swallow it WITHOUT rolling back — exactly what the bug
        # scenario looked like before the fix.
        try:
            store._session.execute(text("INSERT INTO nonexistent_table VALUES (1)"))
        except Exception:
            pass  # session is now in PendingRollback state — not rolled back here
        raise OperationalError("stmt", {}, Exception("db error"))

    with patch.object(store, "update_post_summary", side_effect=corrupt_session_then_raise), \
         patch("app.summarizer.groq_client.GroqClient") as mock_cls, \
         patch("app.summarizer.summary_generator.time") as mock_time:
        mock_client = MagicMock()
        mock_client.summarize_post.return_value = "AI 摘要"
        mock_cls.return_value = mock_client
        mock_time.sleep = MagicMock()  # skip 4-second rate-limit delay

        result = notifier.run()

    remaining = store.get_unsent_relevant_posts()
    db.close()
    engine.dispose()

    assert len(remaining) == 0, "posts must be marked sent even after summarization DB error"
    assert result["posts_included"] == 1


def test_run_summarization_uses_reference_time_as_date_string(news_store):
    """_run_summarization should use reference_time's date for the report title, not today."""
    ref = datetime(2026, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
    _insert_relevant_post_at(news_store, "p1", ref - timedelta(hours=1))
    news_store.commit()

    captured_date: list[str] = []

    class FakeGenerator:
        def summarize_batch(self, posts): pass
        def assemble_report(self, posts, date_str):
            captured_date.append(date_str)
            return f"# Report {date_str}"

    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        groq_api_key="fake-key",
    )
    with patch("app.summarizer.groq_client.GroqClient"), \
         patch("app.summarizer.summary_generator.SummaryGenerator", return_value=FakeGenerator()):
        notifier._run_summarization(
            [news_store.get_unsent_relevant_posts(limit=1)[0]],
            reference_time=ref,
        )

    assert len(captured_date) == 1
    assert captured_date[0] == "2026-01-15"


# ---------------------------------------------------------------------------
# Per-channel sent flags (Phase 3)
# ---------------------------------------------------------------------------

def test_run_marks_email_sent_on_email_success(news_store):
    _insert_relevant_post(news_store, "email_ok_p1")
    smtp_config = {
        "host": "smtp.example.com", "port": 587,
        "user": "u", "password": "p",
        "from": "f@e.com", "to": "t@e.com",
    }
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=smtp_config,
        webhook_url=None,
    )
    with patch("app.notifier.digest_notifier.smtplib") as mock_smtp:
        mock_smtp.SMTP.return_value.__enter__.return_value = MagicMock()
        notifier.run()

    posts = news_store.query_posts()
    assert posts[0].email_sent is True


def test_run_does_not_mark_email_sent_on_failure(news_store):
    _insert_relevant_post(news_store, "email_fail_p1")
    smtp_config = {
        "host": "smtp.fail.com", "port": 587,
        "user": "u", "password": "p",
        "from": "f@e.com", "to": "t@e.com",
    }
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=smtp_config,
        webhook_url=None,
    )
    with patch("app.notifier.digest_notifier.smtplib") as mock_smtp:
        mock_smtp.SMTP.return_value.__enter__.side_effect = Exception("SMTP error")
        notifier.run()

    posts = news_store.query_posts()
    assert posts[0].email_sent is False


def test_run_marks_webhook_sent_on_webhook_success(news_store):
    _insert_relevant_post(news_store, "webhook_ok_p1")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url="https://hooks.example.com/ok",
    )
    with patch("app.notifier.digest_notifier.httpx") as mock_httpx:
        mock_httpx.post.return_value = MagicMock(status_code=200)
        notifier.run()

    posts = news_store.query_posts()
    assert posts[0].webhook_sent is True


def test_run_does_not_mark_webhook_sent_on_failure(news_store):
    _insert_relevant_post(news_store, "webhook_fail_p1")
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url="https://hooks.example.com/fail",
    )
    with patch("app.notifier.digest_notifier.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("connection error")
        notifier.run()

    posts = news_store.query_posts()
    assert posts[0].webhook_sent is False


# ---------------------------------------------------------------------------
# Phase B: semantic re-ranking via user_context
# ---------------------------------------------------------------------------

def test_generate_digest_fetches_double_pool_when_reranking_enabled(news_store):
    """When embedding_service + user_context are set, candidate pool is 2x top_n."""
    for i in range(30):
        _insert_relevant_post(news_store, f"rerank_{i}", score=10.0)

    mock_svc = MagicMock()
    mock_svc.embed.return_value = [0.1] * 384

    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        top_n=10,
        embedding_service=mock_svc,
        user_context="I build AI agents",
    )

    with patch("app.embeddings.vector_search.rank_by_user_context", return_value=list(range(20))) as mock_rank:
        # patch returns a list of 20 ints (not posts) to avoid type issues
        with patch.object(news_store, "get_unsent_relevant_posts", wraps=news_store.get_unsent_relevant_posts) as mock_store:
            notifier.generate_digest()
            # Should have requested 20 candidates (top_n * 2)
            mock_store.assert_called_once()
            call_limit = mock_store.call_args[1].get("limit") or mock_store.call_args[0][0]
            assert call_limit == 20


def test_generate_digest_skips_reranking_without_user_context(news_store):
    """No re-ranking when user_context is empty, even with embedding_service."""
    for i in range(15):
        _insert_relevant_post(news_store, f"noctx_{i}", score=10.0)

    mock_svc = MagicMock()
    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        top_n=5,
        embedding_service=mock_svc,
        user_context="",  # empty — no re-ranking
    )

    with patch("app.embeddings.vector_search.rank_by_user_context") as mock_rank:
        notifier.generate_digest()
        mock_rank.assert_not_called()


def test_generate_digest_skips_reranking_without_embedding_service(news_store):
    """No re-ranking when embedding_service is None."""
    for i in range(15):
        _insert_relevant_post(news_store, f"nosvc_{i}", score=10.0)

    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        top_n=5,
        embedding_service=None,
        user_context="I build AI agents",
    )

    with patch("app.embeddings.vector_search.rank_by_user_context") as mock_rank:
        notifier.generate_digest()
        mock_rank.assert_not_called()


def test_generate_digest_returns_top_n_after_reranking(news_store):
    """Final result is always capped at top_n even after re-ranking."""
    for i in range(30):
        _insert_relevant_post(news_store, f"cap_{i}", score=10.0)

    mock_svc = MagicMock()
    mock_svc.embed.return_value = [0.1] * 384

    notifier = DigestNotifier(
        news_store=news_store,
        smtp_config=None,
        webhook_url=None,
        top_n=5,
        embedding_service=mock_svc,
        user_context="context",
    )

    # rank_by_user_context is imported inside the method, patch at source module
    with patch("app.embeddings.vector_search.rank_by_user_context") as mock_rank:
        mock_candidates = [MagicMock() for _ in range(10)]
        mock_rank.return_value = mock_candidates
        result = notifier.generate_digest()
        assert len(result) == 5
