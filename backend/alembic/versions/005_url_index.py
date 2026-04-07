"""Add index on posts.url for fast URL-based dedup lookup.

Revision ID: 005
Revises: 004
Create Date: 2026-04-06
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.create_index("ix_posts_url", ["url"])


def downgrade() -> None:
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.drop_index("ix_posts_url")
