"""Tests for highlight_scorer (Phase 18.2)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.briefing.highlight_scorer import (
    compute_highlight_score,
    format_highlight_section,
    get_top_highlights,
)

_NOW = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)


def _make_post(
    source="hackernews",
    score=7.0,
    hours_old=12,
    url="https://example.com/1",
    content="Test article about LLM",
):
    p = MagicMock()
    p.source = source
    p.relevance_score = score
    p.posted_at = _NOW - timedelta(hours=hours_old)
    p.url = url
    p.content = content
    return p


# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------

def test_score_hackernews_recent():
    p = _make_post(source="hackernews", score=8.0, hours_old=10)
    score = compute_highlight_score(p, reference_time=_NOW)
    # relevance=8*0.5=4.0, source=2*0.3=0.6, recency=1.0*0.2=0.2 → 4.8
    assert abs(score - 4.8) < 0.001


def test_score_arxiv_same_as_unknown_source():
    # arxiv removed from SOURCE_WEIGHTS — falls back to 1.0 (same as reddit/unknown)
    arxiv = _make_post(source="arxiv", score=7.0, hours_old=5)
    reddit = _make_post(source="reddit", score=7.0, hours_old=5)
    assert compute_highlight_score(arxiv, _NOW) == compute_highlight_score(reddit, _NOW)


def test_score_recency_decay_under_48h():
    p = _make_post(hours_old=30)  # 24–48h range
    score = compute_highlight_score(p, reference_time=_NOW)
    # recency=0.5
    p2 = _make_post(hours_old=10)  # < 24h
    score2 = compute_highlight_score(p2, reference_time=_NOW)
    assert score2 > score  # fresher = higher


def test_score_no_recency_beyond_48h():
    p = _make_post(hours_old=72)
    score = compute_highlight_score(p, reference_time=_NOW)
    # recency=0.0
    p2 = _make_post(hours_old=5)
    score2 = compute_highlight_score(p2, reference_time=_NOW)
    assert score2 > score


def test_score_none_relevance():
    p = _make_post(score=None)
    p.relevance_score = None
    score = compute_highlight_score(p, reference_time=_NOW)
    assert score >= 0.0


def test_custom_weights():
    p = _make_post(source="hackernews", score=5.0, hours_old=5)
    w = {"relevance": 1.0, "source": 0.0, "recency": 0.0}
    score = compute_highlight_score(p, reference_time=_NOW, weights=w)
    assert abs(score - 5.0) < 0.001


# ---------------------------------------------------------------------------
# get_top_highlights
# ---------------------------------------------------------------------------

def test_get_top_highlights_returns_top_3():
    posts = [_make_post(score=float(i), hours_old=1) for i in range(10)]
    top = get_top_highlights(posts, n=3, reference_time=_NOW)
    assert len(top) == 3


def test_get_top_highlights_sorted_by_score():
    p_low = _make_post(source="reddit", score=3.0, hours_old=60, url="low")
    p_high = _make_post(source="arxiv", score=9.0, hours_old=5, url="high")
    p_mid = _make_post(source="hackernews", score=6.0, hours_old=10, url="mid")
    top = get_top_highlights([p_low, p_high, p_mid], n=3, reference_time=_NOW)
    assert top[0].url == "high"


def test_get_top_highlights_fewer_than_n():
    posts = [_make_post(score=5.0)]
    top = get_top_highlights(posts, n=3, reference_time=_NOW)
    assert len(top) == 1


# ---------------------------------------------------------------------------
# format_highlight_section
# ---------------------------------------------------------------------------

def test_format_highlight_section_contains_header():
    posts = [_make_post()]
    md = format_highlight_section(posts, reference_time=_NOW)
    assert "⭐ 今日精選" in md


def test_format_highlight_section_contains_url():
    posts = [_make_post(url="https://test.com/article")]
    md = format_highlight_section(posts, reference_time=_NOW)
    assert "https://test.com/article" in md
