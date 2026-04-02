"""Tests for RedditFetcher."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.fetcher.reddit_fetcher import RedditFetcher, _USER_AGENT


def _make_post_data(post_id: str = "abc123", title: str = "AI agent tool") -> dict:
    return {
        "id": post_id,
        "title": title,
        "selftext": "Some body",
        "author": "reddit_user",
        "permalink": f"/r/MachineLearning/comments/{post_id}/ai_agent/",
        "created_utc": 1743494400.0,  # 2025-04-01
        "score": 42,
    }


def _make_listing(posts: list[dict], after: str = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.is_success = True
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "data": {
            "children": [{"data": p} for p in posts],
            "after": after,
        }
    }
    return resp


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def fetcher(news_store, mock_client):
    return RedditFetcher(
        subreddits=["MachineLearning"],
        fetch_limit=10,
        news_store=news_store,
        _client=mock_client,
    )


def test_reddit_fetch_subreddit_returns_posts(fetcher, mock_client):
    mock_client.get.return_value = _make_listing(
        [_make_post_data("p1"), _make_post_data("p2")]
    )
    results = fetcher.fetch()
    assert len(results) == 2
    assert results[0].source == "reddit"
    assert results[0].external_id == "p1"
    assert "reddit.com" in results[0].url


def test_reddit_uses_custom_user_agent(news_store):
    """Fetcher must initialise httpx.Client with custom User-Agent header."""
    fetcher = RedditFetcher(subreddits=[], news_store=news_store)
    assert fetcher._client.headers.get("user-agent") == _USER_AGENT


def test_reddit_fetch_skips_private_subreddit(fetcher, mock_client):
    resp_403 = MagicMock()
    resp_403.status_code = 403
    mock_client.get.return_value = resp_403
    results = fetcher.fetch()
    assert results == []


def test_reddit_keyword_search_skips_on_error(news_store, mock_client):
    fetcher = RedditFetcher(
        subreddits=[],
        keywords=["ai agent"],
        news_store=news_store,
        _client=mock_client,
    )
    err_resp = MagicMock()
    err_resp.is_success = False
    mock_client.get.return_value = err_resp
    results = fetcher.fetch()
    assert results == []


def test_reddit_pagination_follows_after_token(fetcher, mock_client):
    mock_client.get.side_effect = [
        _make_listing([_make_post_data("p1"), _make_post_data("p2")], after="t3_next"),
        _make_listing([_make_post_data("p3")]),
    ]
    results = fetcher.fetch()
    assert len(results) == 3
    second_call_params = mock_client.get.call_args_list[1][1]["params"]
    assert second_call_params["after"] == "t3_next"


def test_reddit_dedup_excludes_existing_ids(fetcher, news_store, mock_client):
    news_store.upsert_post({
        "source": "reddit", "external_id": "p1",
        "author_handle": "u", "content": "c", "url": "u",
        "posted_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    })
    mock_client.get.return_value = _make_listing(
        [_make_post_data("p1"), _make_post_data("p2")]
    )
    results = fetcher.fetch()
    assert len(results) == 1
    assert results[0].external_id == "p2"


def test_reddit_rate_limit_respects_retry_after(fetcher, mock_client, mocker):
    sleep_mock = mocker.patch("app.fetcher.reddit_fetcher.time.sleep")
    rate_limited = MagicMock()
    rate_limited.status_code = 429
    rate_limited.headers = {"Retry-After": "30"}
    success = _make_listing([_make_post_data("p1")])
    mock_client.get.side_effect = [rate_limited, success]
    results = fetcher.fetch()
    sleep_mock.assert_called_with(30)
    assert len(results) == 1


def test_reddit_points_populated(fetcher, mock_client):
    mock_client.get.return_value = _make_listing([_make_post_data("p1")])
    results = fetcher.fetch()
    assert results[0].points == 42
