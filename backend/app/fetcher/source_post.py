"""Unified post schema shared by all source adapters."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourcePost:
    source: str       # "hackernews" | "reddit" | "github"
    external_id: str  # source-specific unique ID
    author_handle: str
    content: str      # title + body, truncated to 2000 chars
    url: str
    posted_at: datetime  # UTC
    points: int | None = None  # community votes: HN points, Reddit score, GitHub stars
