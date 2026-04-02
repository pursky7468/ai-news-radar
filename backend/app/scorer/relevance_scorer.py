"""RelevanceScorer: TF-IDF + keyword weight scoring for X posts."""
from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default keyword dictionary
# ---------------------------------------------------------------------------

DEFAULT_KEYWORDS: dict = {
    "high_weight": {
        "agent": [
            "ai agent",
            "ai agents",
            "agent skill",
            "agent skills",
            "multi-agent",
            "multi agent",
            "agentic",
            "autonomous agent",
            "tool use",
            "tool calling",
            "function calling",
            "mcp",
            "model context protocol",
            "langchain",
            "autogen",
            "crewai",
            "smolagents",
            "rag",
            "retrieval augmented",
        ],
        "tool": [
            "langchain",
            "llamaindex",
            "llama index",
            "semantic kernel",
            "dspy",
            "instructor",
            "guidance",
        ],
    },
    "standard_weight": {
        "model": [
            "llm",
            "large language model",
            "gpt",
            "claude",
            "gemini",
            "mistral",
            "llama",
            "qwen",
            "fine-tuning",
            "fine tuning",
            "rlhf",
            "sft",
            "alignment",
        ],
        "ai-general": [
            "artificial intelligence",
            "openai",
            "anthropic",
            "google deepmind",
            "deepmind",
            "hugging face",
            "huggingface",
            "ai research",
            "ai model",
            "foundation model",
        ],
    },
    "threshold": 5,
}

# Label mapping: keyword group name → label string
_GROUP_LABEL_MAP: dict[str, str] = {
    "agent": "ai-agent",
    "tool": "ai-tool",
    "model": "ai-model",
    "ai-general": "ai-model",
}

# Weight per tier
_HIGH_WEIGHT = 3
_STANDARD_WEIGHT = 1

# Normalisation constant: raw score mapped to 0-10 scale (3 high-weight hits → ~9)
_MAX_RAW_SCORE = 10.0


def _normalize(raw: float) -> float:
    """Map raw score to 0–10, clamped."""
    return min(10.0, (raw / _MAX_RAW_SCORE) * 10.0)


class RelevanceScorer:
    def __init__(
        self,
        *,
        news_store=None,
        keywords_config_path: Optional[str] = None,
        threshold: float = 5.0,
    ) -> None:
        self._store = news_store
        self.threshold = threshold
        self._keywords = self._load_config(keywords_config_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_post(self, post: dict) -> dict:
        """Return dict with relevance_score, labels, is_relevant."""
        source = post.get("source")
        external_id = post.get("external_id")

        # Cache check
        if self._store and source and external_id:
            cached = self._store.get_post_by_source_and_external_id(source, external_id)
            if cached and cached.relevance_score is not None:
                return {
                    "relevance_score": cached.relevance_score,
                    "labels": cached.labels,
                    "is_relevant": cached.is_relevant,
                }

        return self._compute_score(post)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_score(self, post: dict) -> dict:
        content = (post.get("content") or "").lower()
        raw_score = 0.0
        fired_groups: set[str] = set()

        for group_name, terms in self._keywords.get("high_weight", {}).items():
            for term in terms:
                if _term_in_text(term, content):
                    raw_score += _HIGH_WEIGHT
                    fired_groups.add(group_name)

        for group_name, terms in self._keywords.get("standard_weight", {}).items():
            for term in terms:
                if _term_in_text(term, content):
                    raw_score += _STANDARD_WEIGHT
                    fired_groups.add(group_name)

        score = _normalize(raw_score)
        # Community vote bonus: up to +3 pts for high-vote posts (300+ votes → max bonus)
        points = post.get("points") or 0
        score = min(10.0, score + min(points / 100, 3.0))
        labels = _groups_to_labels(fired_groups) if fired_groups else ["other"]
        is_relevant = score >= self.threshold

        return {"relevance_score": round(score, 2), "labels": labels, "is_relevant": is_relevant}

    def _load_config(self, path: Optional[str]) -> dict:
        if path:
            p = Path(path)
            if p.exists():
                try:
                    with p.open() as f:
                        return yaml.safe_load(f) or DEFAULT_KEYWORDS
                except Exception as exc:
                    logger.warning("Failed to load keywords config %s: %s", path, exc)
            else:
                logger.warning("Keywords config not found at %s, using defaults", path)
        return DEFAULT_KEYWORDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _term_in_text(term: str, text: str) -> bool:
    # Use word-boundary-aware search for single words, substring for phrases
    if " " in term or "-" in term:
        return term in text
    return bool(re.search(rf"\b{re.escape(term)}\b", text))


def _groups_to_labels(groups: set[str]) -> list[str]:
    seen: list[str] = []
    for group in sorted(groups):
        label = _GROUP_LABEL_MAP.get(group)
        if label and label not in seen:
            seen.append(label)
    return seen if seen else ["other"]
