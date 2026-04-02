"""Tests for HackerNewsFetcher."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.fetcher.hn_fetcher import HackerNewsFetcher


def _make_response(hits: list[dict], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"hits": hits}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _make_hit(object_id: str = "42", title: str = "AI agent demo") -> dict:
    return {
        "objectID": object_id,
        "title": title,
        "story_text": "Some body text",
        "author": "hn_user",
        "url": "https://example.com/ai-agent",
        "created_at": "2026-03-01T12:00:00Z",
        "points": 150,
    }


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def fetcher(news_store, mock_client):
    return HackerNewsFetcher(
        keywords=["ai agent"],
        fetch_limit=10,
        news_store=news_store,
        _client=mock_client,
    )


def test_hn_fetch_by_keywords_returns_posts(fetcher, mock_client):
    mock_client.get.return_value = _make_response([_make_hit("1"), _make_hit("2")])
    # second page empty to stop pagination
    mock_client.get.side_effect = [
        _make_response([_make_hit("1"), _make_hit("2")]),
        _make_response([]),
    ]
    results = fetcher.fetch()
    assert len(results) == 2
    assert results[0].source == "hackernews"
    assert results[0].external_id == "1"
    assert results[0].author_handle == "hn_user"


def test_hn_fetch_empty_results(fetcher, mock_client):
    mock_client.get.return_value = _make_response([])
    results = fetcher.fetch()
    assert results == []


def test_hn_pagination_follows_page_param(fetcher, mock_client):
    mock_client.get.side_effect = [
        _make_response([_make_hit(str(i)) for i in range(5)]),
        _make_response([_make_hit(str(i)) for i in range(5, 9)]),
        _make_response([]),
    ]
    results = fetcher.fetch()
    assert len(results) == 9
    # verify page param increments
    calls = mock_client.get.call_args_list
    assert calls[0][1]["params"]["page"] == 0
    assert calls[1][1]["params"]["page"] == 1


def test_hn_pagination_stops_at_limit(news_store, mock_client):
    fetcher = HackerNewsFetcher(
        keywords=["ai agent"], fetch_limit=3, news_store=news_store, _client=mock_client
    )
    mock_client.get.return_value = _make_response([_make_hit(str(i)) for i in range(20)])
    results = fetcher.fetch()
    assert len(results) == 3


def test_hn_dedup_excludes_existing_ids(fetcher, news_store, mock_client):
    news_store.upsert_post({
        "source": "hackernews", "external_id": "1",
        "author_handle": "u", "content": "c", "url": "u",
        "posted_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    })
    mock_client.get.side_effect = [
        _make_response([_make_hit("1"), _make_hit("2")]),
        _make_response([]),
    ]
    results = fetcher.fetch()
    assert len(results) == 1
    assert results[0].external_id == "2"


def test_hn_consecutive_errors_skip_source(fetcher, mock_client):
    err = Exception("connection error")
    mock_client.get.side_effect = [err, err, err]
    results = fetcher.fetch()
    assert results == []


def test_hn_points_populated(fetcher, mock_client):
    mock_client.get.side_effect = [
        _make_response([_make_hit("1")]),
        _make_response([]),
    ]
    results = fetcher.fetch()
    assert results[0].points == 150


def test_hn_points_missing_returns_none(fetcher, mock_client):
    hit = _make_hit("2")
    hit.pop("points", None)
    mock_client.get.side_effect = [_make_response([hit]), _make_response([])]
    results = fetcher.fetch()
    assert results[0].points is None
