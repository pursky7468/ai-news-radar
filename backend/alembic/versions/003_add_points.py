"""Add points column to posts table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-31
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column("points", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("points")
