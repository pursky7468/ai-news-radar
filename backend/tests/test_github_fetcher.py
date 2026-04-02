"""Tests for GitHubFetcher."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.fetcher.github_fetcher import GitHubFetcher


def _make_repo(full_name: str = "owner/repo", description: str = "AI agent framework") -> dict:
    return {
        "full_name": full_name,
        "description": description,
        "topics": ["llm", "agent"],
        "html_url": f"https://github.com/{full_name}",
        "owner": {"login": full_name.split("/")[0]},
        "pushed_at": "2026-03-01T10:00:00Z",
        "created_at": "2026-02-01T10:00:00Z",
        "stargazers_count": 500,
    }


def _make_search_response(repos: list[dict], link: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"items": repos, "total_count": len(repos)}
    resp.headers = {"X-RateLimit-Remaining": "29", "Link": link}
    resp.raise_for_status = MagicMock()
    return resp


def _make_release(tag: str = "v1.0.0", repo: str = "owner/repo") -> dict:
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "New features and bug fixes",
        "html_url": f"https://github.com/{repo}/releases/tag/{tag}",
        "published_at": "2026-03-01T12:00:00Z",
    }


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def fetcher(news_store, mock_client):
    return GitHubFetcher(
        keywords=["ai agent"],
        monitored_repos=[],
        fetch_limit=10,
        news_store=news_store,
        _client=mock_client,
    )


def test_github_fetch_recent_high_star_repos(fetcher, mock_client):
    mock_client.get.return_value = _make_search_response([_make_repo("owner/ai-agent")])
    results = fetcher.fetch()
    assert len(results) == 1
    assert results[0].source == "github"
    assert results[0].external_id == "owner/ai-agent"
    assert results[0].author_handle == "owner"


def test_github_fetch_releases_returns_new_release(news_store, mock_client):
    fetcher = GitHubFetcher(
        keywords=[],
        monitored_repos=["owner/repo"],
        news_store=news_store,
        _client=mock_client,
    )
    release_resp = MagicMock()
    release_resp.status_code = 200
    release_resp.json.return_value = _make_release("v2.0.0", "owner/repo")
    release_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = release_resp
    results = fetcher.fetch()
    assert len(results) == 1
    assert results[0].external_id == "owner/repo@v2.0.0"


def test_github_fetch_release_skips_if_already_stored(news_store, mock_client):
    news_store.upsert_post({
        "source": "github", "external_id": "owner/repo@v2.0.0",
        "author_handle": "owner", "content": "c", "url": "u",
        "posted_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    })
    fetcher = GitHubFetcher(
        keywords=[],
        monitored_repos=["owner/repo"],
        news_store=news_store,
        _client=mock_client,
    )
    release_resp = MagicMock()
    release_resp.status_code = 200
    release_resp.json.return_value = _make_release("v2.0.0", "owner/repo")
    release_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = release_resp
    results = fetcher.fetch()
    assert results == []


def test_github_unauthenticated_sleeps_between_search_calls(news_store, mock_client, mocker):
    sleep_mock = mocker.patch("app.fetcher.github_fetcher.time.sleep")
    fetcher = GitHubFetcher(
        keywords=["ai", "llm"],
        monitored_repos=[],
        github_token="",  # unauthenticated
        news_store=news_store,
        _client=mock_client,
    )
    mock_client.get.return_value = _make_search_response([])
    fetcher.fetch()
    # Should sleep between keyword search calls
    assert sleep_mock.call_count >= 1
    sleep_mock.assert_any_call(6)


def test_github_authenticated_uses_token_header(news_store):
    fetcher = GitHubFetcher(
        keywords=[], monitored_repos=[],
        github_token="mytoken123", news_store=news_store,
    )
    assert fetcher._client.headers.get("authorization") == "Bearer mytoken123"


def test_github_search_rate_limit_waits_for_reset(fetcher, mock_client, mocker):
    sleep_mock = mocker.patch("app.fetcher.github_fetcher.time.sleep")
    mocker.patch("app.fetcher.github_fetcher.time.time", return_value=1000)
    rate_limited_resp = MagicMock()
    rate_limited_resp.status_code = 200
    rate_limited_resp.json.return_value = {"items": []}
    rate_limited_resp.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1060",
        "Link": "",
    }
    rate_limited_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = rate_limited_resp
    fetcher.fetch()
    sleep_mock.assert_any_call(61)  # 1060 - 1000 + 1


def test_github_pagination_follows_link_header(fetcher, mock_client):
    page1 = _make_search_response(
        [_make_repo("owner/repo1")],
        link='<https://api.github.com/search/repositories?page=2>; rel="next"',
    )
    page2 = _make_search_response([_make_repo("owner/repo2")])
    mock_client.get.side_effect = [page1, page2]
    results = fetcher.fetch()
    assert len(results) == 2
    assert mock_client.get.call_count == 2


def test_github_repo_points_populated(fetcher, mock_client):
    mock_client.get.return_value = _make_search_response([_make_repo("owner/ai-agent")])
    results = fetcher.fetch()
    assert results[0].points == 500


def test_github_release_points_is_zero(news_store, mock_client):
    fetcher = GitHubFetcher(
        keywords=[],
        monitored_repos=["owner/repo"],
        news_store=news_store,
        _client=mock_client,
    )
    release_resp = MagicMock()
    release_resp.status_code = 200
    release_resp.json.return_value = _make_release("v1.0.0", "owner/repo")
    release_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = release_resp
    results = fetcher.fetch()
    assert results[0].points == 0
