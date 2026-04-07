from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)       # "hackernews" | "reddit" | "github"
    external_id = Column(String, nullable=False)  # source-specific unique ID
    author_handle = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=False)
    fetched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    relevance_score = Column(Float, nullable=True)
    points = Column(Integer, nullable=True)
    is_relevant = Column(Boolean, nullable=False, default=False)
    labels = Column(JSON, nullable=False, default=list)
    digest_sent = Column(Boolean, nullable=False, default=False)
    summary_zh = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_posts_source_external_id"),
        Index("ix_posts_posted_at", "posted_at"),
        Index("ix_posts_relevance_score", "relevance_score"),
        Index("ix_posts_is_relevant", "is_relevant"),
        Index("ix_posts_source", "source"),
        Index("ix_posts_url", "url"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    content = Column(Text, nullable=False)       # Markdown zh-TW report
    post_count = Column(Integer, nullable=False)
    model_used = Column(String, nullable=False)


class SystemState(Base):
    __tablename__ = "system_state"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
