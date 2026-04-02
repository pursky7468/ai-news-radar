"""Tests for NewsStore — TDD Red/Green cycle."""
from datetime import datetime, timedelta, timezone

import pytest

from app.store.news_store import NewsStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_post(**kwargs):
    defaults = dict(
        source="hackernews",
        external_id="post_001",
        author_handle="user_a",
        content="AI agent uses tool calling to accomplish tasks",
        url="https://news.ycombinator.com/item?id=post_001",
        posted_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        relevance_score=8.5,
        is_relevant=True,
        labels=["ai-agent"],
        digest_sent=False,
    )
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def test_upsert_inserts_new_post(news_store: NewsStore):
    post = make_post()
    news_store.upsert_post(post)
    results = news_store.query_posts()
    assert len(results) == 1
    assert results[0].external_id == "post_001"
    assert results[0].source == "hackernews"


def test_upsert_deduplicates_by_source_and_external_id(news_store: NewsStore):
    post = make_post()
    news_store.upsert_post(post)
    # second upsert same (source, external_id) with updated score
    news_store.upsert_post({**post, "relevance_score": 9.0})
    results = news_store.query_posts()
    assert len(results) == 1
    assert results[0].relevance_score == 9.0


def test_upsert_allows_same_external_id_different_source(news_store: NewsStore):
    news_store.upsert_post(make_post(source="hackernews", external_id="123"))
    news_store.upsert_post(make_post(source="reddit", external_id="123"))
    results = news_store.query_posts()
    assert len(results) == 2


# ---------------------------------------------------------------------------
# exists_by_source_and_external_id
# ---------------------------------------------------------------------------

def test_exists_by_source_and_external_id_true(news_store: NewsStore):
    news_store.upsert_post(make_post(source="reddit", external_id="abc123"))
    assert news_store.exists_by_source_and_external_id("reddit", "abc123") is True


def test_exists_by_source_and_external_id_false(news_store: NewsStore):
    assert news_store.exists_by_source_and_external_id("reddit", "nonexistent") is False


# ---------------------------------------------------------------------------
# Query filters
# ---------------------------------------------------------------------------

def test_query_filters_by_label(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1", labels=["ai-agent"], is_relevant=True))
    news_store.upsert_post(make_post(external_id="p2", labels=["ai-model"], is_relevant=True))
    results = news_store.query_posts(label="ai-agent")
    assert len(results) == 1
    assert results[0].external_id == "p1"


def test_query_filters_by_min_score(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1", relevance_score=9.0))
    news_store.upsert_post(make_post(external_id="p2", relevance_score=4.0))
    results = news_store.query_posts(min_score=7.0)
    assert len(results) == 1
    assert results[0].external_id == "p1"


def test_query_filters_by_date_range(news_store: NewsStore):
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    news_store.upsert_post(make_post(external_id="p1", posted_at=now))
    news_store.upsert_post(make_post(external_id="p2", posted_at=now - timedelta(days=5)))
    results = news_store.query_posts(
        from_date=now - timedelta(days=1),
        to_date=now + timedelta(days=1),
    )
    assert len(results) == 1
    assert results[0].external_id == "p1"


def test_query_filters_by_keyword(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1", content="multi-agent system demo"))
    news_store.upsert_post(make_post(external_id="p2", content="unrelated cooking tips"))
    results = news_store.query_posts(keyword="multi-agent")
    assert len(results) == 1
    assert results[0].external_id == "p1"


def test_query_filters_by_source(news_store: NewsStore):
    news_store.upsert_post(make_post(source="hackernews", external_id="p1"))
    news_store.upsert_post(make_post(source="reddit", external_id="p2"))
    news_store.upsert_post(make_post(source="github", external_id="p3"))
    results = news_store.query_posts(source="reddit")
    assert len(results) == 1
    assert results[0].source == "reddit"


def test_query_filters_by_since(news_store: NewsStore):
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    news_store.upsert_post(make_post(external_id="p1", posted_at=base + timedelta(hours=2)))
    news_store.upsert_post(make_post(external_id="p2", posted_at=base - timedelta(hours=2)))
    results = news_store.query_posts(since=base)
    assert len(results) == 1
    assert results[0].external_id == "p1"


# ---------------------------------------------------------------------------
# Digest
# ---------------------------------------------------------------------------

def test_mark_digest_sent(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1"))
    post = news_store.query_posts()[0]
    news_store.mark_digest_sent([post.id])
    updated = news_store.query_posts()[0]
    assert updated.digest_sent is True


def test_get_unsent_relevant_posts(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1", is_relevant=True, digest_sent=False))
    news_store.upsert_post(make_post(external_id="p2", is_relevant=True, digest_sent=True))
    news_store.upsert_post(make_post(external_id="p3", is_relevant=False, digest_sent=False))
    results = news_store.get_unsent_relevant_posts()
    assert len(results) == 1
    assert results[0].external_id == "p1"


# ---------------------------------------------------------------------------
# System state (last_fetch_at)
# ---------------------------------------------------------------------------

def test_get_last_fetch_at_returns_null_before_first_fetch(news_store: NewsStore):
    result = news_store.get_last_fetch_at()
    assert result is None


def test_update_last_fetch_at(news_store: NewsStore):
    ts = datetime(2026, 3, 24, 8, 0, tzinfo=timezone.utc)
    news_store.update_last_fetch_at(ts)
    result = news_store.get_last_fetch_at()
    assert result == ts


# ---------------------------------------------------------------------------
# Lookup by ID
# ---------------------------------------------------------------------------

def test_get_post_by_id_found(news_store: NewsStore):
    news_store.upsert_post(make_post(external_id="p1"))
    post = news_store.query_posts()[0]
    found = news_store.get_post_by_id(post.id)
    assert found is not None
    assert found.external_id == "p1"


def test_get_post_by_id_not_found(news_store: NewsStore):
    result = news_store.get_post_by_id(9999)
    assert result is None
