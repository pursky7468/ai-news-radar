"""Pydantic schemas for the REST API."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Post(BaseModel):
    id: int
    x_post_id: str
    author_handle: str
    content: str
    url: str
    posted_at: datetime
    fetched_at: datetime
    relevance_score: Optional[float] = None
    is_relevant: bool
    labels: List[str]
    digest_sent: bool

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
