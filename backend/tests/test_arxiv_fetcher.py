"""Tests for ArxivFetcher (Phase 17.3)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.fetcher.arxiv_fetcher import ArxivFetcher

# Minimal valid ArXiv Atom feed XML
_NOW = datetime.now(timezone.utc)
_RECENT = (_NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
_OLD = (_NOW - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

_ATOM_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  {entries}
</feed>"""

_ENTRY_TEMPLATE = """\
<entry>
  <id>http://arxiv.org/abs/{arxiv_id}</id>
  <title>{title}</title>
  <summary>{abstract}</summary>
  <published>{published}</published>
</entry>"""


def _make_atom(entries_xml: str) -> str:
    return _ATOM_TEMPLATE.format(entries=entries_xml)


def _make_entry(arxiv_id="2403.00001", title="Test Paper", abstract="Test abstract.", published=None):
    return _ENTRY_TEMPLATE.format(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        published=published or _RECENT,
    )


def _make_fetcher(response_xml: str, store=None):
    client = MagicMock()
    resp = MagicMock()
    resp.text = response_xml
    resp.raise_for_status = MagicMock()
    client.get.return_value = resp
    return ArxivFetcher(
        categories=["cs.AI"],
        keywords=["LLM"],
        max_results=10,
        news_store=store,
        _client=client,
    )


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------

def test_fetch_returns_source_posts():
    xml = _make_atom(_make_entry())
    fetcher = _make_fetcher(xml)
    results = fetcher.fetch()
    assert len(results) == 1
    post = results[0]
    assert post.source == "arxiv"
    assert post.external_id == "2403.00001"
    assert post.url == "https://arxiv.org/abs/2403.00001"
    assert post.points is None
    assert post.discussion_url is None


def test_fetch_content_is_title_plus_abstract():
    xml = _make_atom(_make_entry(title="My Title", abstract="My abstract."))
    fetcher = _make_fetcher(xml)
    results = fetcher.fetch()
    assert results[0].content.startswith("My Title. My abstract.")


def test_fetch_multiple_entries():
    entries = _make_entry("2403.00001") + _make_entry("2403.00002")
    xml = _make_atom(entries)
    fetcher = _make_fetcher(xml)
    assert len(fetcher.fetch()) == 2


# ---------------------------------------------------------------------------
# Pre-filter: skip papers older than 7 days
# ---------------------------------------------------------------------------

def test_fetch_skips_old_papers():
    old_entry = _make_entry(arxiv_id="2403.00001", published=_OLD)
    recent_entry = _make_entry(arxiv_id="2403.00002", published=_RECENT)
    xml = _make_atom(old_entry + recent_entry)
    fetcher = _make_fetcher(xml)
    results = fetcher.fetch()
    assert len(results) == 1
    assert results[0].external_id == "2403.00002"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_fetch_deduplicates_via_store():
    store = MagicMock()
    store.exists_by_source_and_external_id.return_value = True
    xml = _make_atom(_make_entry())
    fetcher = _make_fetcher(xml, store=store)
    results = fetcher.fetch()
    assert results == []


# ---------------------------------------------------------------------------
# HTTP error
# ---------------------------------------------------------------------------

def test_fetch_returns_empty_on_http_error():
    client = MagicMock()
    client.get.side_effect = Exception("connection refused")
    fetcher = ArxivFetcher(
        categories=["cs.AI"],
        keywords=[],
        max_results=10,
        _client=client,
    )
    assert fetcher.fetch() == []


def test_fetch_returns_empty_on_non_200():
    client = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("404")
    client.get.return_value = resp
    fetcher = ArxivFetcher(categories=["cs.AI"], keywords=[], _client=client)
    assert fetcher.fetch() == []


# ---------------------------------------------------------------------------
# Empty feed
# ---------------------------------------------------------------------------

def test_fetch_empty_feed():
    xml = _make_atom("")
    fetcher = _make_fetcher(xml)
    assert fetcher.fetch() == []
