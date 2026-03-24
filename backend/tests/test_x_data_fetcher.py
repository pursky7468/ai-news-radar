"""Tests for XDataFetcher — TDD Red/Green cycle (Tweepy mocked)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.fetcher.x_data_fetcher import XDataFetcher


def _make_tweet(tweet_id: str, text: str, author_id: str = "u1"):
    t = MagicMock()
    t.id = tweet_id
    t.text = text
    t.author_id = author_id
    t.created_at = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    return t


def _make_response(tweets=None, next_token=None, errors=None):
    resp = MagicMock()
    resp.data = tweets or []
    resp.meta = MagicMock()
    resp.meta.next_token = next_token
    resp.errors = errors or []
    return resp


def _make_user_response(user_id: str, username: str):
    resp = MagicMock()
    user = MagicMock()
    user.id = user_id
    user.username = username
    resp.data = user
    return resp


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def fetcher(news_store, mock_client):
    return XDataFetcher(
        bearer_token="test_token",
        news_store=news_store,
        _client=mock_client,
    )


# ---------------------------------------------------------------------------
# Keyword fetch
# ---------------------------------------------------------------------------

def test_fetch_by_keywords_returns_posts(fetcher, mock_client):
    tweet = _make_tweet("t1", "AI agent demo using tool calling")
    mock_client.search_recent_tweets.return_value = _make_response(tweets=[tweet])
    results = fetcher.fetch_by_keywords(["ai agent"])
    assert len(results) == 1
    assert results[0]["x_post_id"] == "t1"


def test_fetch_by_keywords_empty_results(fetcher, mock_client):
    mock_client.search_recent_tweets.return_value = _make_response(tweets=[])
    results = fetcher.fetch_by_keywords(["ai agent"])
    assert results == []


# ---------------------------------------------------------------------------
# Account fetch
# ---------------------------------------------------------------------------

def test_fetch_from_account_returns_posts(fetcher, mock_client):
    mock_client.get_user.return_value = _make_user_response("u123", "AnthropicAI")
    tweet = _make_tweet("t2", "New Claude release", author_id="u123")
    mock_client.get_users_tweets.return_value = _make_response(tweets=[tweet])
    results = fetcher.fetch_from_accounts(["AnthropicAI"])
    assert len(results) == 1
    assert results[0]["x_post_id"] == "t2"


def test_fetch_skips_unknown_account(fetcher, mock_client):
    resp = MagicMock()
    resp.data = None
    mock_client.get_user.return_value = resp
    results = fetcher.fetch_from_accounts(["ghost_account_xyz"])
    assert results == []


# ---------------------------------------------------------------------------
# Rate limit handling
# ---------------------------------------------------------------------------

def test_rate_limit_waits_and_retries(fetcher, mock_client):
    import tweepy

    rate_err = tweepy.errors.TooManyRequests(MagicMock(headers={"x-rate-limit-reset": "0"}))
    tweet = _make_tweet("t3", "AI agent post")
    mock_client.search_recent_tweets.side_effect = [
        rate_err,
        _make_response(tweets=[tweet]),
    ]
    with patch("time.sleep"):
        results = fetcher.fetch_by_keywords(["ai agent"])
    assert len(results) == 1


def test_rate_limit_skips_after_max_retries(fetcher, mock_client):
    import tweepy

    rate_err = tweepy.errors.TooManyRequests(MagicMock(headers={"x-rate-limit-reset": "0"}))
    mock_client.search_recent_tweets.side_effect = [rate_err, rate_err, rate_err, rate_err]
    with patch("time.sleep"):
        results = fetcher.fetch_by_keywords(["ai agent"])
    assert results == []


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_dedup_excludes_existing_post_ids(fetcher, mock_client, news_store, post_factory):
    from datetime import datetime, timezone

    # Pre-store a post
    news_store.upsert_post({
        "x_post_id": "existing_t1",
        "author_handle": "user",
        "content": "already stored",
        "url": "https://x.com/i/web/status/existing_t1",
        "posted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    })
    tweet = _make_tweet("existing_t1", "already stored")
    mock_client.search_recent_tweets.return_value = _make_response(tweets=[tweet])
    results = fetcher.fetch_by_keywords(["ai"])
    assert all(r["x_post_id"] != "existing_t1" for r in results)


def test_dedup_includes_new_post_ids(fetcher, mock_client):
    tweet = _make_tweet("brand_new_t99", "brand new AI agent post")
    mock_client.search_recent_tweets.return_value = _make_response(tweets=[tweet])
    results = fetcher.fetch_by_keywords(["ai agent"])
    assert any(r["x_post_id"] == "brand_new_t99" for r in results)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def test_pagination_follows_next_token(fetcher, mock_client):
    page1 = _make_response(
        tweets=[_make_tweet("t10", "post 1")],
        next_token="tok_abc",
    )
    page2 = _make_response(
        tweets=[_make_tweet("t11", "post 2")],
        next_token=None,
    )
    mock_client.search_recent_tweets.side_effect = [page1, page2]
    results = fetcher.fetch_by_keywords(["ai"], max_results=100)
    assert len(results) == 2


def test_pagination_stops_at_limit(fetcher, mock_client):
    # Each page returns 1 result, but limit is 1
    page1 = _make_response(
        tweets=[_make_tweet("t20", "post 1")],
        next_token="tok_xyz",
    )
    mock_client.search_recent_tweets.return_value = page1
    results = fetcher.fetch_by_keywords(["ai"], max_results=1)
    assert len(results) <= 1
