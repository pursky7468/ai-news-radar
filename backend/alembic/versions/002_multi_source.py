"""Replace x_post_id with source + external_id for multi-source support.

Revision ID: 002
Revises: 001
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"


def upgrade() -> None:
    # SQLite does not support DROP COLUMN or ADD CONSTRAINT directly.
    # Use batch_alter_table with recreate='always' to fully rebuild the table,
    # which handles unnamed constraints (SQLite auto-names them) without errors.
    with op.batch_alter_table("posts", schema=None, recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.String(), nullable=False, server_default="hackernews")
        )
        batch_op.add_column(
            sa.Column("external_id", sa.String(), nullable=False, server_default="")
        )
        batch_op.drop_column("x_post_id")
        batch_op.create_unique_constraint(
            "uq_posts_source_external_id", ["source", "external_id"]
        )

    op.create_index("ix_posts_source", "posts", ["source"])


def downgrade() -> None:
    op.drop_index("ix_posts_source", table_name="posts")
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_constraint("uq_posts_source_external_id", type_="unique")
        batch_op.add_column(
            sa.Column("x_post_id", sa.String(), nullable=False, server_default="")
        )
        batch_op.drop_column("external_id")
        batch_op.drop_column("source")
        batch_op.create_unique_constraint("x_post_id", ["x_post_id"])
