"""Add SQLite FTS5 virtual table for full-text search on posts.

Creates articles_fts mirroring title (content[:100]) and summary columns,
plus three sync triggers (INSERT / UPDATE / DELETE) to keep it in sync.

Revision ID: 006
Revises: 005
Create Date: 2026-04-07
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FTS5 virtual table — content= means it shadows the posts table
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
        USING fts5(
            title,
            summary,
            content='posts',
            content_rowid='id',
            tokenize='unicode61'
        )
    """)

    # Populate from existing rows (title = first 100 chars of content)
    op.execute("""
        INSERT INTO articles_fts(rowid, title, summary)
        SELECT id, substr(content, 1, 100), COALESCE(summary_zh, '')
        FROM posts
    """)

    # INSERT trigger
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_fts_insert
        AFTER INSERT ON posts BEGIN
            INSERT INTO articles_fts(rowid, title, summary)
            VALUES (new.id, substr(new.content, 1, 100), COALESCE(new.summary_zh, ''));
        END
    """)

    # UPDATE trigger (delete+insert pattern required for content= FTS5 tables)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_fts_update
        AFTER UPDATE ON posts BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary)
            VALUES ('delete', old.id, substr(old.content, 1, 100), COALESCE(old.summary_zh, ''));
            INSERT INTO articles_fts(rowid, title, summary)
            VALUES (new.id, substr(new.content, 1, 100), COALESCE(new.summary_zh, ''));
        END
    """)

    # DELETE trigger
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_fts_delete
        AFTER DELETE ON posts BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary)
            VALUES ('delete', old.id, substr(old.content, 1, 100), COALESCE(old.summary_zh, ''));
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS posts_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS posts_fts_update")
    op.execute("DROP TRIGGER IF EXISTS posts_fts_insert")
    op.execute("DROP TABLE IF EXISTS articles_fts")
