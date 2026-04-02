"""
Integration tests for rate limit handling across multi-source fetchers.

Tests:
- MultiSourceFetcher continues when a source raises an exception
- FetchPipeline stores partial results when some sources are rate-limited
- FetchPipeline handles empty results gracefully
- GitHub rate limit: sleep derived from X-RateLimit-Reset header
- Reddit rate limit: sleep derived from Retry-After header
"""
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.fetcher.github_fetcher import GitHubFetcher
from app.fetcher.hn_fetcher import HackerNewsFetcher
from app.fetcher.multi_source_fetcher import MultiSourceFetcher
from app.fetcher.reddit_fetcher import RedditFetcher
from app.fetcher.source_post import SourcePost
from app.pipeline.fetch_pipeline import FetchPipeline
from app.scorer.relevance_scorer import RelevanceScorer


def _make_source_post(source: str, ext_id: str) -> SourcePost:
    return SourcePost(
        source=source,
        external_id=ext_id,
        author_handle="user",
        content="AI agent post",
        url=f"https://example.com/{ext_id}",
        posted_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# 1. MultiSourceFetcher continues after a source raises
# ---------------------------------------------------------------------------

def test_multisource_continues_after_source_exception(news_store):
    """When one adapter raises, MultiSourceFetcher skips it and returns results from others."""
    hn = MagicMock()
    hn.fetch.side_effect = Exception("HN connection error")

    reddit = MagicMock()
    reddit.fetch.return_value = [_make_source_post("reddit", "r1")]

    github = MagicMock()
    github.fetch.return_value = []

    fetcher = MultiSourceFetcher(hn=hn, reddit=reddit, github=github)
    results = fetcher.fetch()

    assert len(results) == 1
    assert results[0].source == "reddit"


def test_multisource_all_sources_failed_returns_empty(news_store):
    """When all adapters raise, MultiSourceFetcher returns []."""
    err = Exception("network error")
    hn = MagicMock(); hn.fetch.side_effect = err
    reddit = MagicMock(); reddit.fetch.side_effect = err
    github = MagicMock(); github.fetch.side_effect = err

    fetcher = MultiSourceFetcher(hn=hn, reddit=reddit, github=github)
    assert fetcher.fetch() == []


# ---------------------------------------------------------------------------
# 2. FetchPipeline stores partial results when sources return partial data
# ---------------------------------------------------------------------------

def test_pipeline_stores_partial_results(news_store):
    """FetchPipeline stores successfully fetched posts even when some sources failed."""
    hn = MagicMock(); hn.fetch.return_value = [_make_source_post("hackernews", "h1")]
    reddit = MagicMock(); reddit.fetch.side_effect = Exception("rate limited")
    github = MagicMock(); github.fetch.return_value = []

    multi_fetcher = MultiSourceFetcher(hn=hn, reddit=reddit, github=github)
    scorer = RelevanceScorer(news_store=news_store)
    pipeline = FetchPipeline(news_store=news_store, fetcher=multi_fetcher, scorer=scorer)

    result = pipeline.run()

    assert result["fetched"] == 1
    stored = news_store.query_posts()
    assert len(stored) == 1
    assert stored[0].source == "hackernews"


def test_pipeline_handles_all_rate_limited(news_store):
    """FetchPipeline.run() returns zero counts when all sources are exhausted."""
    hn = MagicMock(); hn.fetch.side_effect = Exception("rate limited")
    reddit = MagicMock(); reddit.fetch.side_effect = Exception("rate limited")
    github = MagicMock(); github.fetch.side_effect = Exception("rate limited")

    multi_fetcher = MultiSourceFetcher(hn=hn, reddit=reddit, github=github)
    scorer = RelevanceScorer(news_store=news_store)
    pipeline = FetchPipeline(news_store=news_store, fetcher=multi_fetcher, scorer=scorer)

    result = pipeline.run()

    assert result["fetched"] == 0
    assert result["stored"] == 0
    assert news_store.query_posts() == []


# ---------------------------------------------------------------------------
# 3. GitHub rate limit: wait time from X-RateLimit-Reset header
# ---------------------------------------------------------------------------

def test_github_rate_limit_wait_derived_from_reset_header(news_store, mocker):
    """GitHubFetcher sleeps for the correct duration calculated from reset timestamp."""
    sleep_mock = mocker.patch("app.fetcher.github_fetcher.time.sleep")
    future_reset = int(time.time()) + 30
    mocker.patch("app.fetcher.github_fetcher.time.time", return_value=int(time.time()))

    mock_client = MagicMock()
    rate_resp = MagicMock()
    rate_resp.status_code = 200
    rate_resp.json.return_value = {"items": []}
    rate_resp.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(future_reset),
        "Link": "",
    }
    rate_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = rate_resp

    fetcher = GitHubFetcher(
        keywords=["ai agent"], monitored_repos=[],
        news_store=news_store, _client=mock_client,
    )
    fetcher.fetch()

    # Should sleep for ~31s (reset - now + 1)
    sleep_calls = [c[0][0] for c in sleep_mock.call_args_list]
    assert any(25 <= s <= 35 for s in sleep_calls), f"Expected ~31s sleep, got {sleep_calls}"


# ---------------------------------------------------------------------------
# 4. Reddit rate limit: wait time from Retry-After header
# ---------------------------------------------------------------------------

def test_reddit_rate_limit_wait_derived_from_retry_after(news_store, mocker):
    """RedditFetcher sleeps for the Retry-After duration on 429 responses."""
    sleep_mock = mocker.patch("app.fetcher.reddit_fetcher.time.sleep")
    mock_client = MagicMock()

    rate_resp = MagicMock()
    rate_resp.status_code = 429
    rate_resp.headers = {"Retry-After": "45"}

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.is_success = True
    success_resp.raise_for_status = MagicMock()
    success_resp.json.return_value = {
        "data": {"children": [], "after": None}
    }

    mock_client.get.side_effect = [rate_resp, success_resp]

    fetcher = RedditFetcher(
        subreddits=["MachineLearning"], news_store=news_store, _client=mock_client,
    )
    fetcher.fetch()

    sleep_mock.assert_called_with(45)
