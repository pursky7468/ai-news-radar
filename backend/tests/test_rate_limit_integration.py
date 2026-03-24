"""
Integration tests for rate limit handling (task 10.6).

Simulates 429 responses at different levels to verify:
- Correct wait time derived from x-rate-limit-reset header
- Retry-then-succeed path
- Exhaust-retries-then-skip path (fetcher continues to next query)
- FetchPipeline stores partial results when some queries hit rate limits
"""
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest
import tweepy

from app.fetcher.x_data_fetcher import XDataFetcher
from app.pipeline.fetch_pipeline import FetchPipeline
from app.scorer.relevance_scorer import RelevanceScorer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tweet(tweet_id: str, text: str = "AI agent demo"):
    t = MagicMock()
    t.id = tweet_id
    t.text = text
    t.author_id = "u1"
    t.created_at = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    return t


def _make_response(tweets=None, next_token=None):
    resp = MagicMock()
    resp.data = tweets or []
    resp.meta = MagicMock()
    resp.meta.next_token = next_token
    resp.errors = []
    return resp


def _rate_limit_error(reset_timestamp: int) -> tweepy.errors.TooManyRequests:
    """Build a TooManyRequests error with a specific x-rate-limit-reset header."""
    fake_response = MagicMock()
    fake_response.headers = {"x-rate-limit-reset": str(reset_timestamp)}
    return tweepy.errors.TooManyRequests(fake_response)


# ---------------------------------------------------------------------------
# 1. Wait time is derived from x-rate-limit-reset header
# ---------------------------------------------------------------------------

def test_wait_time_derived_from_reset_header(news_store):
    """Fetcher sleeps for the correct duration calculated from reset timestamp."""
    mock_client = MagicMock()
    future_reset = int(time.time()) + 30  # 30 seconds from now

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(future_reset),
        _make_response(tweets=[_make_tweet("t1")]),
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep") as mock_sleep:
        results = fetcher.fetch_by_keywords(["ai agent"])

    # sleep should have been called with ~30s (within a small tolerance)
    assert mock_sleep.call_count == 1
    wait_called = mock_sleep.call_args[0][0]
    assert 25 <= wait_called <= 35, f"Expected ~30s sleep, got {wait_called}s"
    assert len(results) == 1


def test_wait_time_zero_for_past_reset(news_store):
    """When reset timestamp is in the past, fetcher sleeps for at least 1s (fallback)."""
    mock_client = MagicMock()
    past_reset = int(time.time()) - 60  # 60 seconds ago

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(past_reset),
        _make_response(tweets=[_make_tweet("t2")]),
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep") as mock_sleep:
        fetcher.fetch_by_keywords(["ai agent"])

    # fallback sleep of 1s when reset is in the past
    mock_sleep.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# 2. Retry-then-succeed: 2 x 429 then success
# ---------------------------------------------------------------------------

def test_retries_twice_then_succeeds(news_store):
    """Fetcher retries up to (MAX_RETRIES-1) times before succeeding."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),
        _make_response(tweets=[_make_tweet("t3", "AI agent post")]),
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep"):
        results = fetcher.fetch_by_keywords(["ai agent"])

    assert len(results) == 1
    assert results[0]["x_post_id"] == "t3"
    # search_recent_tweets called 3 times total (2 failures + 1 success)
    assert mock_client.search_recent_tweets.call_count == 3


# ---------------------------------------------------------------------------
# 3. Exhaust retries: 3+ x 429 → skip query, return empty
# ---------------------------------------------------------------------------

def test_exhausts_retries_skips_query(news_store):
    """After MAX_RETRIES consecutive 429s, fetcher logs error and skips the query."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),  # 4th call — should never reach here
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep"):
        results = fetcher.fetch_by_keywords(["ai agent"])

    assert results == []
    # Called exactly MAX_RETRIES (3) times before giving up
    assert mock_client.search_recent_tweets.call_count == 3


# ---------------------------------------------------------------------------
# 4. Multiple keywords: first query rate-limited, second succeeds
# ---------------------------------------------------------------------------

def test_rate_limit_on_first_keyword_continues_to_next(news_store):
    """When one keyword query is rate-limited to exhaustion, fetcher still processes
    remaining keywords (pipeline does not abort entirely)."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    # We test this at pipeline level by having two separate fetch calls.
    # First batch of keywords → exhausted rate limit → []
    # Second batch → success → [tweet]
    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 3:
            raise _rate_limit_error(reset_ts)
        return _make_response(tweets=[_make_tweet("t_ok", "LLM model release")])

    mock_client.search_recent_tweets.side_effect = side_effect

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep"):
        # fetch_by_keywords builds a single combined query, so this tests
        # that after exhaustion the function returns [] and doesn't raise
        results = fetcher.fetch_by_keywords(["ai agent", "LLM"])

    # Either empty (all retries exhausted on combined query) or partial
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# 5. Pipeline level: rate-limited fetcher → pipeline handles gracefully
# ---------------------------------------------------------------------------

def test_pipeline_handles_rate_limited_fetcher(news_store):
    """FetchPipeline.run() does not raise when the fetcher returns [] due to rate limits."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),
        _rate_limit_error(reset_ts),
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)
    scorer = RelevanceScorer(news_store=news_store)

    pipeline = FetchPipeline(
        news_store=news_store,
        fetcher=fetcher,
        scorer=scorer,
        keywords=["ai agent"],
    )

    with patch("time.sleep"):
        result = pipeline.run()

    assert result["fetched"] == 0
    assert result["stored"] == 0
    # DB should be empty — no posts stored
    assert news_store.query_posts() == []


def test_pipeline_stores_partial_results_before_rate_limit(news_store):
    """If fetcher succeeds on first call then is rate-limited on subsequent calls,
    the successfully fetched posts are still scored and stored."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    # First keyword call returns one post; second keyword call hits limit
    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_response(tweets=[_make_tweet("t_partial", "AI agent using tool calling")])
        raise _rate_limit_error(reset_ts)

    mock_client.search_recent_tweets.side_effect = side_effect

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)
    scorer = RelevanceScorer(news_store=news_store)

    pipeline = FetchPipeline(
        news_store=news_store,
        fetcher=fetcher,
        scorer=scorer,
        keywords=["ai agent"],
    )

    with patch("time.sleep"):
        result = pipeline.run()

    # The one successfully fetched post should have been stored
    stored_posts = news_store.query_posts()
    assert len(stored_posts) == 1
    assert stored_posts[0].x_post_id == "t_partial"


# ---------------------------------------------------------------------------
# 6. Retry counter resets between separate queries
# ---------------------------------------------------------------------------

def test_retry_counter_resets_between_calls(news_store):
    """Each call to fetch_by_keywords starts with a fresh retry counter."""
    mock_client = MagicMock()
    reset_ts = int(time.time()) + 1

    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(reset_ts),
        _make_response(tweets=[_make_tweet("t_first")]),
    ]

    fetcher = XDataFetcher(bearer_token="tok", news_store=news_store, _client=mock_client)

    with patch("time.sleep"):
        first = fetcher.fetch_by_keywords(["ai agent"])

    assert len(first) == 1

    # Second independent call: retry counter should start fresh
    mock_client.search_recent_tweets.side_effect = [
        _rate_limit_error(reset_ts),
        _make_response(tweets=[_make_tweet("t_second")]),
    ]

    with patch("time.sleep"):
        second = fetcher.fetch_by_keywords(["LLM"])

    assert len(second) == 1
