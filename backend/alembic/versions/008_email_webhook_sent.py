"""Add email_sent and webhook_sent per-channel flags to posts table.

Replaces the single digest_sent flag with per-channel tracking so that
a webhook failure does not prevent email from being marked delivered.
digest_sent is kept as a deprecated backward-compat column.

Revision ID: 008
Revises: 007
Create Date: 2026-04-12
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "posts",
        sa.Column("webhook_sent", sa.Boolean(), nullable=False, server_default="0"),
    )
    # Backfill: rows already delivered via digest_sent=True count as sent on both channels
    op.execute("UPDATE posts SET email_sent = 1, webhook_sent = 1 WHERE digest_sent = 1")


def downgrade() -> None:
    op.drop_column("posts", "webhook_sent")
    op.drop_column("posts", "email_sent")
