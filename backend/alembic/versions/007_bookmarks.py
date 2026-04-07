"""Add bookmarks table for article bookmarking with optional notes.

Revision ID: 007
Revises: 006
Create Date: 2026-04-07
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bookmarks_article_id", "bookmarks", ["article_id"])


def downgrade() -> None:
    op.drop_index("ix_bookmarks_article_id", table_name="bookmarks")
    op.drop_table("bookmarks")
