"""Add summary_zh to posts and create reports table.

Revision ID: 004
Revises: 003
Create Date: 2026-04-03
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column("summary_zh", sa.Text(), nullable=True))

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("post_count", sa.Integer(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("summary_zh")
