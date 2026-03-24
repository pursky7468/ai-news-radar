"""FetchPipeline: orchestrate fetch → score → upsert cycle."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FetchPipeline:
    def __init__(
        self,
        news_store,
        fetcher,
        scorer,
        keywords: list[str],
        accounts: list[str] | None = None,
    ) -> None:
        self._store = news_store
        self._fetcher = fetcher
        self._scorer = scorer
        self._keywords = keywords
        self._accounts = accounts or []

    def run(self) -> dict:
        # 1. Fetch
        posts = self._fetcher.fetch_by_keywords(self._keywords)
        if self._accounts:
            posts += self._fetcher.fetch_from_accounts(self._accounts)

        fetched_count = len(posts)
        logger.info("Pipeline: fetched %d new posts", fetched_count)

        if not posts:
            logger.info("Pipeline: nothing to score or store")
            return {"fetched": 0, "scored": 0, "stored": 0}

        # 2. Score
        scored_posts = []
        for post in posts:
            try:
                scores = self._scorer.score_post(post)
                scored_posts.append({**post, **scores})
            except Exception as exc:
                logger.error("Scoring error for post %s: %s", post.get("x_post_id"), exc)

        logger.info("Pipeline: scored %d posts", len(scored_posts))

        # 3. Upsert
        stored_count = 0
        for post in scored_posts:
            try:
                self._store.upsert_post(post)
                stored_count += 1
            except Exception as exc:
                logger.error("Store error for post %s: %s", post.get("x_post_id"), exc)

        # 4. Update last fetch timestamp
        self._store.update_last_fetch_at(datetime.now(timezone.utc))
        logger.info("Pipeline: stored %d posts", stored_count)

        return {"fetched": fetched_count, "scored": len(scored_posts), "stored": stored_count}
