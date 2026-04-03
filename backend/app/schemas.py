"""Pydantic schemas for the REST API."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, model_validator


class Post(BaseModel):
    id: int
    source: str
    external_id: str
    author_handle: str
    content: str
    url: str
    posted_at: datetime
    fetched_at: datetime
    relevance_score: Optional[float] = None
    points: Optional[int] = None
    summary_zh: Optional[str] = None
    is_relevant: bool
    labels: List[str]
    digest_sent: bool
    discussion_url: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _compute_discussion_url(self) -> "Post":
        if self.source == "hackernews" and self.discussion_url is None:
            self.discussion_url = (
                f"https://news.ycombinator.com/item?id={self.external_id}"
            )
        return self


class ReportResponse(BaseModel):
    id: int
    generated_at: datetime
    content: str
    post_count: int
    model_used: str

    model_config = {"from_attributes": True}


class PaginatedNewsResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[Post]


class DigestTriggerResult(BaseModel):
    posts_included: int
    email_sent: bool
    webhook_sent: bool


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    db: str  # "connected" | "disconnected"
    last_fetch_at: Optional[datetime] = None
