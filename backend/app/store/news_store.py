"""NewsStore: persistence layer for fetched and scored X posts."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Post, SystemState

_LAST_FETCH_KEY = "last_fetch_at"


class NewsStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_post(self, data: dict) -> None:
        """Insert or update a post by x_post_id."""
        existing = (
            self._session.query(Post)
            .filter(Post.x_post_id == data["x_post_id"])
            .first()
        )
        if existing:
            existing.relevance_score = data.get("relevance_score", existing.relevance_score)
            existing.is_relevant = data.get("is_relevant", existing.is_relevant)
            existing.labels = data.get("labels", existing.labels)
        else:
            post = Post(
                x_post_id=data["x_post_id"],
                author_handle=data["author_handle"],
                content=data["content"],
                url=data["url"],
                posted_at=data["posted_at"],
                fetched_at=data.get("fetched_at", datetime.now(timezone.utc)),
                relevance_score=data.get("relevance_score"),
                is_relevant=data.get("is_relevant", False),
                labels=data.get("labels", []),
                digest_sent=data.get("digest_sent", False),
            )
            self._session.add(post)
        self._session.flush()

    def mark_digest_sent(self, post_ids: list[int]) -> None:
        """Mark the given post IDs as digest_sent=True."""
        self._session.query(Post).filter(Post.id.in_(post_ids)).update(
            {"digest_sent": True}, synchronize_session="fetch"
        )
        self._session.flush()

    def update_last_fetch_at(self, timestamp: datetime) -> None:
        """Record the most recent successful fetch timestamp."""
        existing = self._session.get(SystemState, _LAST_FETCH_KEY)
        if existing:
            existing.value = timestamp.isoformat()
            existing.updated_at = datetime.now(timezone.utc)
        else:
            self._session.add(
                SystemState(
                    key=_LAST_FETCH_KEY,
                    value=timestamp.isoformat(),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        self._session.flush()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def query_posts(
        self,
        *,
        label: Optional[str] = None,
        min_score: Optional[float] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        sort: str = "date_desc",
        page: int = 1,
        per_page: int = 20,
    ) -> list[Post]:
        q = self._session.query(Post)

        if label is not None:
            # JSON contains — SQLite: use LIKE; Postgres: use @>
            q = q.filter(Post.labels.contains(label))

        if min_score is not None:
            q = q.filter(Post.relevance_score >= min_score)

        if from_date is not None:
            q = q.filter(Post.posted_at >= from_date)

        if to_date is not None:
            q = q.filter(Post.posted_at <= to_date)

        if keyword is not None:
            q = q.filter(Post.content.ilike(f"%{keyword}%"))

        if is_relevant is not None:
            q = q.filter(Post.is_relevant == is_relevant)

        if sort == "score_desc":
            q = q.order_by(Post.relevance_score.desc().nullslast())
        else:
            q = q.order_by(Post.posted_at.desc())

        offset = (page - 1) * per_page
        return q.offset(offset).limit(per_page).all()

    def count_posts(
        self,
        *,
        label: Optional[str] = None,
        min_score: Optional[float] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        is_relevant: Optional[bool] = None,
    ) -> int:
        q = self._session.query(func.count(Post.id))
        if label is not None:
            q = q.filter(Post.labels.contains(label))
        if min_score is not None:
            q = q.filter(Post.relevance_score >= min_score)
        if from_date is not None:
            q = q.filter(Post.posted_at >= from_date)
        if to_date is not None:
            q = q.filter(Post.posted_at <= to_date)
        if keyword is not None:
            q = q.filter(Post.content.ilike(f"%{keyword}%"))
        if is_relevant is not None:
            q = q.filter(Post.is_relevant == is_relevant)
        return q.scalar() or 0

    def get_unsent_relevant_posts(self, limit: int = 20) -> list[Post]:
        return (
            self._session.query(Post)
            .filter(Post.is_relevant == True, Post.digest_sent == False)
            .order_by(Post.relevance_score.desc().nullslast())
            .limit(limit)
            .all()
        )

    def get_post_by_id(self, post_id: int) -> Optional[Post]:
        return self._session.get(Post, post_id)

    def get_post_by_id_by_x(self, x_post_id: str) -> Optional[Post]:
        return (
            self._session.query(Post)
            .filter(Post.x_post_id == x_post_id)
            .first()
        )

    def get_last_fetch_at(self) -> Optional[datetime]:
        row = self._session.get(SystemState, _LAST_FETCH_KEY)
        if row is None or row.value is None:
            return None
        return datetime.fromisoformat(row.value)

    def check_db_alive(self) -> bool:
        """Return True if the database is reachable."""
        try:
            self._session.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception:
            return False
