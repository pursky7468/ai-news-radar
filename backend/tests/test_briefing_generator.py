"""Tests for BriefingGenerator — language validation and retry logic (Phase 2)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from app.briefing.briefing_generator import BriefingGenerator, _validate_language


# ---------------------------------------------------------------------------
# _validate_language unit tests
# ---------------------------------------------------------------------------

class TestValidateLanguage:
    def test_pure_chinese_passes(self):
        assert _validate_language("今日 AI 新聞彙整") is True

    def test_mixed_chinese_english_passes(self):
        assert _validate_language("使用 LangChain 與 RAG pipeline") is True

    def test_english_only_passes(self):
        assert _validate_language("AI agent workflow") is True

    def test_common_cjk_punctuation_passes(self):
        assert _validate_language("重點：Agent 設計、記憶管理") is True

    def test_vietnamese_latin_fails(self):
        # "một" contains Vietnamese characters (extended Latin)
        assert _validate_language("một") is False

    def test_arabic_fails(self):
        assert _validate_language("مرحبا") is False

    def test_thai_fails(self):
        assert _validate_language("สวัสดี") is False

    def test_empty_string_passes(self):
        assert _validate_language("") is True

    def test_numbers_and_symbols_pass(self):
        assert _validate_language("score = min(10, 3.0) — 2026") is True


# ---------------------------------------------------------------------------
# BriefingGenerator._call_groq retry logic
# ---------------------------------------------------------------------------

def _make_generator(tmp_path: Path) -> BriefingGenerator:
    return BriefingGenerator(
        groq_api_key="test-key",
        output_dir=tmp_path,
    )


def _mock_groq_response(text: str):
    resp = MagicMock()
    resp.choices[0].message.content = text
    return resp


class TestBriefingGeneratorRetry:
    def test_valid_language_no_retry(self, tmp_path):
        gen = _make_generator(tmp_path)
        good_text = "今日技術摘要：Agent 協作模式有新進展。"

        with patch("groq.Groq") as MockGroq:
            client = MockGroq.return_value
            client.chat.completions.create.return_value = _mock_groq_response(good_text)
            result = gen._call_groq("some report content")

        assert result == good_text
        assert client.chat.completions.create.call_count == 1

    def test_invalid_language_triggers_retry(self, tmp_path):
        gen = _make_generator(tmp_path)
        bad_text = "một số thông tin"   # Vietnamese
        good_text = "重試後的繁體中文內容。"

        with patch("groq.Groq") as MockGroq:
            client = MockGroq.return_value
            client.chat.completions.create.side_effect = [
                _mock_groq_response(bad_text),
                _mock_groq_response(good_text),
            ]
            result = gen._call_groq("some report content")

        assert result == good_text
        assert client.chat.completions.create.call_count == 2

    def test_retry_fails_adds_warning_header(self, tmp_path):
        gen = _make_generator(tmp_path)
        bad_text = "một số thông tin"  # Vietnamese

        with patch("groq.Groq") as MockGroq:
            client = MockGroq.return_value
            client.chat.completions.create.return_value = _mock_groq_response(bad_text)
            result = gen._call_groq("some report content")

        assert "⚠️ [語言品質警告" in result
        assert client.chat.completions.create.call_count == 2

    def test_generate_skips_when_no_api_key(self, tmp_path):
        gen = BriefingGenerator(groq_api_key="", output_dir=tmp_path)
        result = gen.generate("some content")
        assert result is None

    def test_generate_skips_when_empty_content(self, tmp_path):
        gen = _make_generator(tmp_path)
        result = gen.generate("")
        assert result is None

    def test_generate_saves_file(self, tmp_path):
        from datetime import datetime, timezone
        gen = _make_generator(tmp_path)
        good_text = "今日技術摘要：RAG pipeline 有新突破。"

        with patch("groq.Groq") as MockGroq:
            client = MockGroq.return_value
            client.chat.completions.create.return_value = _mock_groq_response(good_text)
            date = datetime(2026, 4, 12, tzinfo=timezone.utc)
            path = gen.generate("report content", date=date)

        assert path is not None
        assert path.name == "2026-04-12.md"
        assert good_text in path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Phase C: prompt content and report format
# ---------------------------------------------------------------------------

class TestBriefingPromptContent:
    """Verify the briefing prompt includes the required selection criteria."""

    def test_prompt_includes_type_label_explanation(self):
        from app.briefing.briefing_generator import _BRIEFING_PROMPT
        assert "[討論]" in _BRIEFING_PROMPT
        assert "[實測]" in _BRIEFING_PROMPT
        assert "[工具]" in _BRIEFING_PROMPT

    def test_prompt_forbids_template_phrases(self):
        from app.briefing.briefing_generator import _BRIEFING_PROMPT
        assert "可以幫助開發者" in _BRIEFING_PROMPT  # listed as forbidden
        assert "禁止" in _BRIEFING_PROMPT

    def test_prompt_requires_single_dimension_per_article(self):
        from app.briefing.briefing_generator import _BRIEFING_PROMPT
        assert "只能出現在一個維度" in _BRIEFING_PROMPT

    def test_prompt_prefers_discussion_over_tool_announcement(self):
        from app.briefing.briefing_generator import _BRIEFING_PROMPT
        assert "優先選" in _BRIEFING_PROMPT
        assert "[討論]" in _BRIEFING_PROMPT

    def test_retry_prompt_also_forbids_template_phrases(self):
        from app.briefing.briefing_generator import _BRIEFING_RETRY_PROMPT
        assert "禁止" in _BRIEFING_RETRY_PROMPT


class TestPostTypeLabel:
    """Verify _post_type_label correctly classifies posts."""

    def _make_post(self, source, content):
        post = MagicMock()
        post.source = source
        post.content = content
        return post

    def test_reddit_discussion_first_person(self):
        from app.summarizer.summary_generator import _post_type_label
        post = self._make_post("reddit", "I've been building a multi-agent framework for 5 weeks")
        assert _post_type_label(post) == "[討論]"

    def test_reddit_discussion_help_request(self):
        from app.summarizer.summary_generator import _post_type_label
        post = self._make_post("reddit", "Struggling with token exhaustion context management")
        assert _post_type_label(post) == "[討論]"

    def test_reddit_analysis_benchmark(self):
        from app.summarizer.summary_generator import _post_type_label
        post = self._make_post("reddit", "Llama 4 benchmark comparison vs Llama 3.1")
        assert _post_type_label(post) == "[實測]"

    def test_github_tool_default(self):
        from app.summarizer.summary_generator import _post_type_label
        post = self._make_post("github", "A new MCP server for AI agents")
        assert _post_type_label(post) == "[工具]"

    def test_hackernews_news_default(self):
        from app.summarizer.summary_generator import _post_type_label
        post = self._make_post("hackernews", "Anthropic releases new model")
        assert _post_type_label(post) == "[新聞]"

    def test_format_entry_includes_type_label(self):
        from app.summarizer.summary_generator import _format_post_entry
        post = MagicMock()
        post.source = "reddit"
        post.content = "I've been building a RAG pipeline, lessons learned"
        post.relevance_score = 8.0
        post.points = None
        post.url = "https://reddit.com/r/test"
        post.discussion_url = None
        post.summary_zh = "作者分享了 RAG pipeline 的實戰經驗。"
        lines = _format_post_entry(post)
        assert any("[討論]" in line for line in lines)

    def test_format_entry_includes_score(self):
        from app.summarizer.summary_generator import _format_post_entry
        post = MagicMock()
        post.source = "github"
        post.content = "A new agent framework"
        post.relevance_score = 7.5
        post.points = 42
        post.url = "https://github.com/test/repo"
        post.discussion_url = None
        post.summary_zh = "一個新的 agent 框架。"
        lines = _format_post_entry(post)
        header = lines[0]
        assert "score=7.5" in header
        assert "▲ 42" in header
