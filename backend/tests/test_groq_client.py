"""Tests for GroqClient — source-aware prompts, content limit, retry logic."""
from unittest.mock import MagicMock, patch

import pytest

from app.summarizer.groq_client import GroqClient, _build_prompt, _CONTENT_LIMIT


def _make_post(content="AI agent framework", source="hackernews"):
    post = MagicMock()
    post.content = content
    post.source = source
    return post


# ---------------------------------------------------------------------------
# _build_prompt: source-aware routing
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_reddit_prompt_includes_discussion_guidance(self):
        prompt = _build_prompt("reddit", "some content")
        assert "Reddit" in prompt
        assert "具體問題" in prompt
        assert "禁止使用" in prompt

    def test_github_prompt_includes_design_decision_guidance(self):
        prompt = _build_prompt("github", "some content")
        assert "GitHub" in prompt
        assert "設計決策" in prompt
        assert "禁止使用" in prompt

    def test_default_prompt_used_for_hackernews(self):
        prompt = _build_prompt("hackernews", "some content")
        assert "hackernews" in prompt
        assert "禁止使用" in prompt

    def test_content_embedded_in_prompt(self):
        prompt = _build_prompt("reddit", "my specific content here")
        assert "my specific content here" in prompt


# ---------------------------------------------------------------------------
# GroqClient.summarize_post
# ---------------------------------------------------------------------------

class TestGroqClientSummarize:
    @pytest.fixture
    def client(self):
        with patch("app.summarizer.groq_client.Groq") as MockGroq:
            MockGroq.return_value = MagicMock()
            return GroqClient(api_key="fake-key")

    def test_returns_stripped_string(self, client):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "  AI 測試摘要  "
        client._client.chat.completions.create.return_value = mock_resp
        result = client.summarize_post(_make_post())
        assert result == "AI 測試摘要"

    def test_truncates_content_to_limit(self, client):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "摘要"
        client._client.chat.completions.create.return_value = mock_resp
        client.summarize_post(_make_post(content="x" * 2000))
        prompt_used = client._client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "x" * _CONTENT_LIMIT in prompt_used
        assert "x" * (_CONTENT_LIMIT + 1) not in prompt_used

    def test_uses_source_aware_prompt_for_reddit(self, client):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "摘要"
        client._client.chat.completions.create.return_value = mock_resp
        client.summarize_post(_make_post(source="reddit"))
        prompt_used = client._client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "Reddit" in prompt_used

    def test_uses_source_aware_prompt_for_github(self, client):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "摘要"
        client._client.chat.completions.create.return_value = mock_resp
        client.summarize_post(_make_post(source="github"))
        prompt_used = client._client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "GitHub" in prompt_used

    def test_retries_once_on_rate_limit(self, client, mocker):
        from groq import RateLimitError
        sleep_mock = mocker.patch("app.summarizer.groq_client.time.sleep")
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "重試成功"
        client._client.chat.completions.create.side_effect = [
            RateLimitError("429", response=MagicMock(status_code=429), body={}),
            mock_resp,
        ]
        result = client.summarize_post(_make_post())
        assert result == "重試成功"
        sleep_mock.assert_called_once_with(60)

    def test_falls_back_on_repeated_failure(self, client, mocker):
        mocker.patch("app.summarizer.groq_client.time.sleep")
        client._client.chat.completions.create.side_effect = Exception("service down")
        result = client.summarize_post(_make_post(content="AI agent framework released"))
        assert result.startswith("AI agent framework released"[:50])
        assert result.endswith("…")

    def test_fallback_empty_content(self, client, mocker):
        mocker.patch("app.summarizer.groq_client.time.sleep")
        client._client.chat.completions.create.side_effect = Exception("fail")
        result = client.summarize_post(_make_post(content=""))
        assert result == ""
