"""Initial schema: posts and system_state tables.

Revision ID: 001
Revises:
Create Date: 2026-03-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("x_post_id", sa.String(), nullable=False),
        sa.Column("author_handle", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("is_relevant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("digest_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("x_post_id"),
    )
    op.create_index("ix_posts_posted_at", "posts", ["posted_at"])
    op.create_index("ix_posts_relevance_score", "posts", ["relevance_score"])
    op.create_index("ix_posts_is_relevant", "posts", ["is_relevant"])

    op.create_table(
        "system_state",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("system_state")
    op.drop_index("ix_posts_is_relevant", table_name="posts")
    op.drop_index("ix_posts_relevance_score", table_name="posts")
    op.drop_index("ix_posts_posted_at", table_name="posts")
    op.drop_table("posts")
