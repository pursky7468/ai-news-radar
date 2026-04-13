"""Tests for GeminiClient — mocks google.generativeai SDK."""
from unittest.mock import MagicMock, patch

import pytest

from app.summarizer.gemini_client import GeminiClient


@pytest.fixture
def mock_genai(mocker):
    return mocker.patch("app.summarizer.gemini_client.genai")


@pytest.fixture
def client(mock_genai):
    mock_genai.GenerativeModel.return_value = MagicMock()
    return GeminiClient(api_key="fake-key", model="gemini-2.0-flash")


def _make_post(content="AI agent is amazing", source="hackernews"):
    post = MagicMock()
    post.content = content
    post.source = source
    return post


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_summarize_post_returns_string(client, mock_genai):
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(text="  AI 代理人新突破  ")
    result = client.summarize_post(_make_post())
    assert result == "AI 代理人新突破"


def test_summarize_post_truncates_content_to_1500(client, mock_genai):
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(text="摘要")
    long_content = "x" * 2000
    client.summarize_post(_make_post(content=long_content))
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "x" * 1500 in prompt_used
    assert "x" * 1501 not in prompt_used


def test_summarize_post_uses_reddit_prompt(client, mock_genai):
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(text="摘要")
    client.summarize_post(_make_post(source="reddit"))
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "Reddit" in prompt_used
    assert "具體問題" in prompt_used


def test_summarize_post_uses_github_prompt(client, mock_genai):
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(text="摘要")
    client.summarize_post(_make_post(source="github"))
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "GitHub" in prompt_used
    assert "設計決策" in prompt_used


# ---------------------------------------------------------------------------
# 429 retry
# ---------------------------------------------------------------------------

def test_summarize_post_retries_once_on_429(client, mock_genai, mocker):
    sleep_mock = mocker.patch("app.summarizer.gemini_client.time.sleep")
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.side_effect = [
        Exception("429 rate limit exceeded"),
        MagicMock(text="重試成功"),
    ]
    result = client.summarize_post(_make_post())
    assert result == "重試成功"
    sleep_mock.assert_called_once_with(60)


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def test_summarize_post_falls_back_on_repeated_failure(client, mock_genai, mocker):
    mocker.patch("app.summarizer.gemini_client.time.sleep")
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.side_effect = Exception("service unavailable")
    result = client.summarize_post(_make_post(content="AI agent framework released"))
    assert result.startswith("AI agent framework released"[:50])
    assert result.endswith("…")


def test_summarize_post_fallback_empty_content(client, mock_genai, mocker):
    mocker.patch("app.summarizer.gemini_client.time.sleep")
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.side_effect = Exception("fail")
    result = client.summarize_post(_make_post(content=""))
    assert result == ""
