"""NewsStore: persistence layer for fetched and scored posts."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Post, Report, SystemState

_LAST_FETCH_KEY = "last_fetch_at"


class NewsStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_post(self, data: dict) -> None:
        """Insert or update a post by (source, external_id)."""
        existing = (
            self._session.query(Post)
            .filter(Post.source == data["source"], Post.external_id == data["external_id"])
            .first()
        )
        if existing:
            existing.relevance_score = data.get("relevance_score", existing.relevance_score)
            existing.is_relevant = data.get("is_relevant", existing.is_relevant)
            existing.labels = data.get("labels", existing.labels)
        else:
            post = Post(
                source=data["source"],
                external_id=data["external_id"],
                author_handle=data["author_handle"],
                content=data["content"],
                url=data["url"],
                posted_at=data["posted_at"],
                fetched_at=data.get("fetched_at", datetime.now(timezone.utc)),
                relevance_score=data.get("relevance_score"),
                points=data.get("points"),
                is_relevant=data.get("is_relevant", False),
                labels=data.get("labels", []),
                digest_sent=data.get("digest_sent", False),
            )
            self._session.add(post)
        self._session.flush()

    def update_post_summary(self, post_id: int, summary_zh: str) -> None:
        """Cache the zh-TW summary for a post."""
        self._session.query(Post).filter(Post.id == post_id).update(
            {"summary_zh": summary_zh}, synchronize_session="fetch"
        )
        self._session.flush()

    def save_report(self, content: str, post_count: int, model_used: str) -> Report:
        """Persist an assembled Markdown report."""
        report = Report(content=content, post_count=post_count, model_used=model_used)
        self._session.add(report)
        self._session.flush()
        return report

    def get_reports(self, limit: int = 50, offset: int = 0) -> list[Report]:
        """Return all reports ordered by generated_at descending."""
        return (
            self._session.query(Report)
            .order_by(Report.generated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_report_by_id(self, report_id: int) -> Optional[Report]:
        """Return a specific report by ID, or None."""
        return self._session.get(Report, report_id)

    def get_latest_report(self) -> Optional[Report]:
        """Return the most recently generated report, or None."""
        return (
            self._session.query(Report)
            .order_by(Report.generated_at.desc())
            .first()
        )

    def mark_digest_sent(self, post_ids: list[int]) -> None:
        """Mark the given post IDs as digest_sent=True."""
        self._session.query(Post).filter(Post.id.in_(post_ids)).update(
            {"digest_sent": True}, synchronize_session="fetch"
        )
        self._session.flush()

    def rollback(self) -> None:
        """Roll back the current transaction, resetting any pending error state."""
        self._session.rollback()

    def commit(self) -> None:
        """Commit the current session transaction."""
        self._session.commit()

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
        since: Optional[datetime] = None,
        keyword: Optional[str] = None,
        source: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        sort: str = "date_desc",
        page: int = 1,
        per_page: int = 20,
    ) -> list[Post]:
        q = self._session.query(Post)
        q = self._apply_filters(q, label=label, min_score=min_score, from_date=from_date,
                                to_date=to_date, since=since, keyword=keyword, source=source,
                                is_relevant=is_relevant)
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
        since: Optional[datetime] = None,
        keyword: Optional[str] = None,
        source: Optional[str] = None,
        is_relevant: Optional[bool] = None,
    ) -> int:
        q = self._session.query(func.count(Post.id))
        q = self._apply_filters(q, label=label, min_score=min_score, from_date=from_date,
                                to_date=to_date, since=since, keyword=keyword, source=source,
                                is_relevant=is_relevant)
        return q.scalar() or 0

    def get_unsent_relevant_posts(
        self, limit: int = 20, since: Optional[datetime] = None
    ) -> list[Post]:
        q = (
            self._session.query(Post)
            .filter(Post.is_relevant == True, Post.digest_sent == False)
        )
        if since is not None:
            q = q.filter(Post.posted_at >= since)
        return q.order_by(Post.relevance_score.desc().nullslast()).limit(limit).all()

    def get_post_by_url(self, url: str) -> Optional[Post]:
        """Return the first Post matching the given URL, or None."""
        return (
            self._session.query(Post)
            .filter(Post.url == url)
            .first()
        )

    def get_post_by_id(self, post_id: int) -> Optional[Post]:
        return self._session.get(Post, post_id)

    def get_post_by_source_and_external_id(self, source: str, external_id: str) -> Optional[Post]:
        """Return the Post matching (source, external_id), or None."""
        return (
            self._session.query(Post)
            .filter(Post.source == source, Post.external_id == external_id)
            .first()
        )

    def exists_by_source_and_external_id(self, source: str, external_id: str) -> bool:
        """Return True if a post with the given (source, external_id) already exists."""
        return (
            self._session.query(Post.id)
            .filter(Post.source == source, Post.external_id == external_id)
            .first()
        ) is not None

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

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_filters(self, q, *, label, min_score, from_date, to_date, since, keyword,
                       source, is_relevant):
        if label is not None:
            q = q.filter(Post.labels.contains(label))
        if min_score is not None:
            q = q.filter(Post.relevance_score >= min_score)
        if from_date is not None:
            q = q.filter(Post.posted_at >= from_date)
        if to_date is not None:
            q = q.filter(Post.posted_at <= to_date)
        if since is not None:
            q = q.filter(Post.posted_at > since)
        if keyword is not None:
            q = q.filter(Post.content.ilike(f"%{keyword}%"))
        if source is not None:
            q = q.filter(Post.source == source)
        if is_relevant is not None:
            q = q.filter(Post.is_relevant == is_relevant)
        return q
