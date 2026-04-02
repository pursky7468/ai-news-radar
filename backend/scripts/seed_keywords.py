"""
Print default configuration for HN keywords, Reddit subreddits, and monitored GitHub repos.
Usage: python scripts/seed_keywords.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine

from app.config import settings
from app.models import Base

DEFAULT_HN_KEYWORDS = [
    "ai agent", "multi-agent", "agentic", "tool use", "tool calling",
    "function calling", "mcp", "model context protocol",
    "langchain", "autogen", "crewai", "rag", "retrieval augmented",
    "llm", "gpt", "claude", "gemini", "mistral", "llama",
    "artificial intelligence", "openai", "anthropic",
]

DEFAULT_REDDIT_SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA",
    "singularity",
    "artificial",
    "ChatGPT",
    "OpenAI",
]

DEFAULT_GITHUB_REPOS = [
    "langchain-ai/langchain",
    "microsoft/autogen",
    "ollama/ollama",
    "ggerganov/llama.cpp",
    "openai/openai-python",
    "anthropics/anthropic-sdk-python",
    "huggingface/transformers",
]

DEFAULT_GITHUB_KEYWORDS = [
    "ai agent",
    "llm",
    "rag",
    "mcp",
]


def main():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    print("Database tables ensured.\n")

    print(f"HN keywords ({len(DEFAULT_HN_KEYWORDS)}) — set via HN_KEYWORDS env var:")
    for kw in DEFAULT_HN_KEYWORDS:
        print(f"  - {kw}")

    print(f"\nReddit subreddits ({len(DEFAULT_REDDIT_SUBREDDITS)}) — set via REDDIT_SUBREDDITS env var:")
    for sub in DEFAULT_REDDIT_SUBREDDITS:
        print(f"  - r/{sub}")

    print(f"\nGitHub monitored repos ({len(DEFAULT_GITHUB_REPOS)}) — set via GITHUB_MONITORED_REPOS env var:")
    for repo in DEFAULT_GITHUB_REPOS:
        print(f"  - {repo}")

    print(f"\nGitHub search keywords ({len(DEFAULT_GITHUB_KEYWORDS)}) — set via GITHUB_KEYWORDS env var:")
    for kw in DEFAULT_GITHUB_KEYWORDS:
        print(f"  - {kw}")

    print("\nTo customise scoring weights, edit keywords.yaml.")
    print("To customise sources, set the env vars listed above.")


if __name__ == "__main__":
    main()
