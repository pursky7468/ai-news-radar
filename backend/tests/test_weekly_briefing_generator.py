"""Tests for WeeklyBriefingGenerator (Phase 18.1)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.briefing.weekly_briefing_generator import WeeklyBriefingGenerator


def _make_post(score=7.0, content="AI article", url="https://example.com/1", hours_old=12):
    p = MagicMock()
    p.relevance_score = score
    p.content = content
    p.url = url
    p.summary_zh = "中文摘要"
    p.source = "hackernews"
    ref = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)
    p.posted_at = ref - timedelta(hours=hours_old)
    return p


def _make_generator(tmp_path, groq_fn=None):
    gen = WeeklyBriefingGenerator(
        groq_api_key="test-key",
        groq_model="llama-3.3-70b-versatile",
        output_dir=tmp_path / "weekly",
    )
    if groq_fn:
        gen._call_groq = groq_fn
    else:
        gen._call_groq = lambda content: "## 週報內容\n本週趨勢..."
    return gen


# ---------------------------------------------------------------------------
# Skipping logic
# ---------------------------------------------------------------------------

def test_generate_skips_if_no_api_key(tmp_path):
    gen = WeeklyBriefingGenerator(groq_api_key="", output_dir=tmp_path)
    result = gen.generate([_make_post()])
    assert result is None


def test_generate_skips_if_fewer_than_3_posts(tmp_path):
    gen = _make_generator(tmp_path)
    posts = [_make_post()] * 2
    result = gen.generate(posts)
    assert result is None


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def test_generate_creates_weekly_file(tmp_path):
    gen = _make_generator(tmp_path)
    posts = [_make_post()] * 5
    ref = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)
    result = gen.generate(posts, reference_date=ref)
    assert result is not None
    # ISO week for 2026-04-07
    iso_year, iso_week, _ = ref.isocalendar()
    expected = tmp_path / "weekly" / f"{iso_year}-W{iso_week:02d}.md"
    assert result == expected
    assert expected.exists()


def test_generate_file_contains_week_header(tmp_path):
    gen = _make_generator(tmp_path)
    posts = [_make_post()] * 5
    ref = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)
    path = gen.generate(posts, reference_date=ref)
    content = path.read_text(encoding="utf-8")
    assert "AI" in content


def test_generate_skips_if_file_exists(tmp_path):
    gen = _make_generator(tmp_path)
    posts = [_make_post()] * 5
    ref = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)
    # First call creates the file
    path1 = gen.generate(posts, reference_date=ref)
    original_content = path1.read_text(encoding="utf-8")
    # Second call should skip (return same path without re-generating)
    gen._call_groq = lambda _: "DIFFERENT CONTENT"
    path2 = gen.generate(posts, reference_date=ref)
    assert path2 == path1
    assert path2.read_text(encoding="utf-8") == original_content  # not overwritten


# ---------------------------------------------------------------------------
# Prompt content
# ---------------------------------------------------------------------------

def test_generate_calls_groq_with_post_content(tmp_path):
    captured = {}

    def mock_groq(content):
        captured["content"] = content
        return "## 週報"

    gen = _make_generator(tmp_path, groq_fn=mock_groq)
    posts = [_make_post(content="LangChain article", url="https://langchain.com")] * 5
    gen.generate(posts, reference_date=datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc))
    assert "LangChain" in captured.get("content", "")
