"""FetchPipeline: orchestrate fetch → score → upsert → embed cycle."""
from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FetchPipeline:
    def __init__(self, news_store, fetcher, scorer, embedding_service=None) -> None:
        self._store = news_store
        self._fetcher = fetcher
        self._scorer = scorer
        self._embedding_service = embedding_service  # optional; None = embeddings disabled

    def run(self) -> dict:
        # 1. Fetch from all sources
        raw_posts = self._fetcher.fetch()
        # Convert dataclasses to dicts if needed
        posts = [
            dataclasses.asdict(p) if dataclasses.is_dataclass(p) else p
            for p in raw_posts
        ]

        fetched_count = len(posts)
        logger.info("Pipeline: fetched %d new posts", fetched_count)

        if not posts:
            logger.info("Pipeline: nothing to score or store")
            return {"fetched": 0, "scored": 0, "stored": 0, "embedded": 0}

        # 2. Score
        scored_posts = []
        for post in posts:
            try:
                scores = self._scorer.score_post(post)
                scored_posts.append({**post, **scores})
            except Exception as exc:
                logger.error("Scoring error for post %s: %s", post.get("external_id"), exc)

        logger.info("Pipeline: scored %d posts", len(scored_posts))

        # 3. Upsert
        stored_count = 0
        for post in scored_posts:
            try:
                self._store.upsert_post(post)
                stored_count += 1
            except Exception as exc:
                logger.error("Store error for post %s: %s", post.get("external_id"), exc)

        # 4. Update last fetch timestamp and commit
        self._store.update_last_fetch_at(datetime.now(timezone.utc))
        self._store.commit()
        logger.info("Pipeline: stored %d posts", stored_count)

        # 5. Compute embeddings for new posts (non-blocking best-effort)
        embedded_count = 0
        if self._embedding_service is not None:
            embedded_count = self._compute_embeddings()

        return {
            "fetched": fetched_count,
            "scored": len(scored_posts),
            "stored": stored_count,
            "embedded": embedded_count,
        }

    def _compute_embeddings(self) -> int:
        """Compute and store embeddings for posts that don't have one yet."""
        from app.embeddings.embedding_service import serialize

        posts_without = self._store.get_posts_without_embedding(limit=100)
        if not posts_without:
            return 0

        count = 0
        for post in posts_without:
            try:
                embedding = self._embedding_service.embed_text_for_post(post)
                self._store.update_post_embedding(post.id, serialize(embedding))
                count += 1
            except Exception as exc:
                logger.warning("Embedding failed for post %d: %s", post.id, exc)

        if count:
            self._store.commit()
            logger.info("Pipeline: computed embeddings for %d posts", count)

        return count
