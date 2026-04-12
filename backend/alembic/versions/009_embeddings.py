"""Add embedding BLOB column to posts for semantic search.

Revision ID: 009
Revises: 008
Create Date: 2026-04-12
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("posts", "embedding")
