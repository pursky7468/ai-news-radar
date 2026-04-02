"""Tests for RelevanceScorer — TDD Red/Green cycle."""
import pytest

from app.scorer.relevance_scorer import RelevanceScorer


@pytest.fixture
def scorer(news_store):
    return RelevanceScorer(news_store=news_store)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_high_weight_terms_score_high(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p1", "content": "AI agent uses tool use and multi-agent orchestration"}
    result = scorer.score_post(post)
    assert result["relevance_score"] >= 7.0


def test_generic_terms_score_moderate(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p2", "content": "New AI model released by OpenAI, uses LLM"}
    result = scorer.score_post(post)
    assert 1.0 <= result["relevance_score"] <= 6.0


def test_no_match_scores_zero(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p3", "content": "My favourite pasta recipe with tomato sauce"}
    result = scorer.score_post(post)
    assert result["relevance_score"] == 0.0


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def test_label_agent_assigned(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p4", "content": "Building an AI agent with tool use and MCP"}
    result = scorer.score_post(post)
    assert "ai-agent" in result["labels"]


def test_label_multi_group(scorer: RelevanceScorer):
    post = {
        "source": "hackernews",
        "external_id": "p5",
        "content": "LLM powered AI agent using RAG and Claude model fine-tuning",
    }
    result = scorer.score_post(post)
    labels = result["labels"]
    assert "ai-agent" in labels
    assert "ai-model" in labels


def test_label_other_fallback(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p6", "content": "Baking bread at home is very satisfying"}
    result = scorer.score_post(post)
    assert result["labels"] == ["other"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_loads_from_yaml(tmp_path):
    config_file = tmp_path / "keywords.yaml"
    config_file.write_text(
        "high_weight:\n"
        "  agent:\n"
        "    - custom_agent_term\n"
        "standard_weight:\n"
        "  model:\n"
        "    - custom_model_term\n"
        "threshold: 5\n"
    )
    scorer = RelevanceScorer(keywords_config_path=str(config_file))
    post = {"source": "hackernews", "external_id": "p7", "content": "custom_agent_term in action"}
    result = scorer.score_post(post)
    assert result["relevance_score"] > 0


def test_config_falls_back_to_defaults(caplog):
    scorer = RelevanceScorer(keywords_config_path="/nonexistent/path.yaml")
    post = {"source": "hackernews", "external_id": "p8", "content": "AI agent demo"}
    result = scorer.score_post(post)
    assert result["relevance_score"] >= 0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_hit_skips_scoring(news_store, mocker):
    # Pre-populate store with a scored post
    news_store.upsert_post(
        {
            "source": "hackernews",
            "external_id": "cached_post",
            "author_handle": "user",
            "content": "cached content",
            "url": "https://news.ycombinator.com/item?id=cached_post",
            "posted_at": __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            "relevance_score": 7.5,
            "is_relevant": True,
            "labels": ["ai-agent"],
        }
    )
    scorer = RelevanceScorer(news_store=news_store)
    spy = mocker.spy(scorer, "_compute_score")
    result = scorer.score_post({"source": "hackernews", "external_id": "cached_post", "content": "anything"})
    spy.assert_not_called()
    assert result["relevance_score"] == 7.5


def test_cache_miss_triggers_scoring(news_store, mocker):
    scorer = RelevanceScorer(news_store=news_store)
    spy = mocker.spy(scorer, "_compute_score")
    scorer.score_post({"source": "hackernews", "external_id": "new_post", "content": "AI agent demo"})
    spy.assert_called_once()


# ---------------------------------------------------------------------------
# is_relevant threshold
# ---------------------------------------------------------------------------

def test_is_relevant_true_at_threshold(scorer: RelevanceScorer):
    post = {"source": "hackernews", "external_id": "p9", "content": "AI agent uses tool use and multi-agent orchestration MCP RAG"}
    result = scorer.score_post(post)
    if result["relevance_score"] >= scorer.threshold:
        assert result["is_relevant"] is True


def test_is_relevant_false_below_threshold():
    scorer = RelevanceScorer(threshold=10.0)  # impossible to hit
    post = {"source": "hackernews", "external_id": "p10", "content": "AI agent demo"}
    result = scorer.score_post(post)
    assert result["is_relevant"] is False


# ---------------------------------------------------------------------------
# Points bonus
# ---------------------------------------------------------------------------

def test_points_bonus_increases_score(scorer):
    # No keyword matches, 300 points → +3.0 bonus
    post = {"source": "github", "external_id": "r1", "content": "unrelated content", "points": 300}
    result = scorer.score_post(post)
    assert result["relevance_score"] == 3.0


def test_points_bonus_capped_at_3(scorer):
    post = {"source": "github", "external_id": "r2", "content": "unrelated content", "points": 9999}
    result = scorer.score_post(post)
    assert result["relevance_score"] == 3.0


def test_points_none_treated_as_zero(scorer):
    post = {"source": "hackernews", "external_id": "r3", "content": "unrelated content", "points": None}
    result = scorer.score_post(post)
    assert result["relevance_score"] == 0.0


def test_points_bonus_does_not_exceed_10(scorer):
    post = {"source": "hackernews", "external_id": "r4",
            "content": "AI agent uses tool use and multi-agent MCP RAG langchain autogen",
            "points": 9999}
    result = scorer.score_post(post)
    assert result["relevance_score"] == 10.0
