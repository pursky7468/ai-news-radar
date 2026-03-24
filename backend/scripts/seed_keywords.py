"""
Seed the default keyword and account watchlist.
Usage: python scripts/seed_keywords.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Base

DEFAULT_KEYWORDS = [
    "ai agent", "agent skill", "multi-agent", "agentic", "tool use",
    "tool calling", "function calling", "mcp", "model context protocol",
    "langchain", "autogen", "crewai", "rag", "retrieval augmented",
    "llm", "gpt", "claude", "gemini", "mistral", "llama",
    "artificial intelligence", "openai", "anthropic",
]

DEFAULT_ACCOUNTS = [
    "AnthropicAI",
    "OpenAI",
    "LangChainAI",
    "GoogleDeepMind",
    "HuggingFace",
    "NvidiaAI",
]


def main():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    print("Database tables ensured.")
    print(f"\nDefault keywords ({len(DEFAULT_KEYWORDS)}):")
    for kw in DEFAULT_KEYWORDS:
        print(f"  - {kw}")
    print(f"\nDefault monitored accounts ({len(DEFAULT_ACCOUNTS)}):")
    for acc in DEFAULT_ACCOUNTS:
        print(f"  - @{acc}")
    print("\nTo customise, edit keywords.yaml or set MONITORED_ACCOUNTS env var.")


if __name__ == "__main__":
    main()
