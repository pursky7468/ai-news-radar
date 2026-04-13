"""Vector search using in-memory cosine similarity.

No external vector DB required — embeddings are stored as BLOBs in SQLite/PostgreSQL
and loaded into memory for similarity computation. Adequate for <50k posts.

Hybrid search combines FTS5 keyword results with vector results via
Reciprocal Rank Fusion (RRF, k=60).
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from app.embeddings.embedding_service import EmbeddingService, deserialize

logger = logging.getLogger(__name__)

_RRF_K = 60  # RRF constant


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def vector_search(
    query_embedding: list[float],
    store,
    top_k: int = 20,
    since=None,
    is_relevant: Optional[bool] = True,
    exclude_ids: Optional[list[int]] = None,
) -> list:
    """Return top_k posts most similar to query_embedding (cosine similarity).

    Loads all posts with embeddings from DB into memory for comparison.
    """
    posts = store.get_posts_with_embeddings(since=since, is_relevant=is_relevant)
    if not posts:
        return []

    exclude = set(exclude_ids or [])
    query_vec = np.array(query_embedding, dtype=np.float32)

    scored = []
    for post in posts:
        if post.id in exclude:
            continue
        try:
            post_vec = np.array(deserialize(post.embedding), dtype=np.float32)
            sim = _cosine_similarity(query_vec, post_vec)
            scored.append((sim, post))
        except Exception as exc:
            logger.debug("vector_search: skipping post %d — %s", post.id, exc)

    scored.sort(key=lambda x: x[0], reverse=True)
    return [post for _, post in scored[:top_k]]


def hybrid_search(
    query: str,
    embedding_service: EmbeddingService,
    store,
    top_k: int = 10,
    since=None,
    is_relevant: Optional[bool] = True,
) -> list:
    """Hybrid search: FTS5 (keyword) + vector (semantic) merged via RRF.

    Args:
        query:             Natural language query string.
        embedding_service: Used to embed the query.
        store:             NewsStore instance for DB access.
        top_k:             Final number of results to return.
        since:             Optional datetime lower bound on posted_at.
        is_relevant:       Filter by is_relevant flag.

    Returns:
        Deduplicated list of Post objects, RRF-ranked.
    """
    # ── FTS5 keyword search ──────────────────────────────────────────────────
    fts_results = store.query_posts(
        keyword=query,
        since=since,
        is_relevant=is_relevant,
        fts_enabled=True,
        sort="score_desc",
        per_page=20,
    )

    # ── Vector search ────────────────────────────────────────────────────────
    try:
        query_embedding = embedding_service.embed(query)
        vec_results = vector_search(
            query_embedding, store, top_k=20, since=since, is_relevant=is_relevant
        )
    except Exception as exc:
        logger.warning("hybrid_search: vector search failed, falling back to FTS only: %s", exc)
        vec_results = []

    # ── RRF merge ────────────────────────────────────────────────────────────
    scores: dict[int, float] = {}
    id_to_post: dict[int, object] = {}

    for rank, post in enumerate(fts_results):
        scores[post.id] = scores.get(post.id, 0.0) + 1.0 / (_RRF_K + rank + 1)
        id_to_post[post.id] = post

    for rank, post in enumerate(vec_results):
        scores[post.id] = scores.get(post.id, 0.0) + 1.0 / (_RRF_K + rank + 1)
        id_to_post[post.id] = post

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [id_to_post[pid] for pid, _ in ranked[:top_k]]


def rank_by_user_context(
    posts: list,
    user_context: str,
    embedding_service: EmbeddingService,
    relevance_weight: float = 0.6,
    semantic_weight: float = 0.4,
) -> list:
    """Re-rank posts by blending relevance_score with semantic similarity to user_context.

    Useful when many posts share the same relevance_score (e.g., 10.0) and a
    secondary signal is needed to surface the most personally relevant content.

    Formula:
        final_score = relevance_score * relevance_weight
                    + cosine_similarity * 10 * semantic_weight

    Args:
        posts:            Candidate posts (already filtered by relevance_score).
        user_context:     Free-text description of what the user cares about.
        embedding_service: Used to embed user_context.
        relevance_weight: Weight for keyword relevance_score (default 0.6).
        semantic_weight:  Weight for semantic similarity, scaled to 0–10 (default 0.4).

    Returns:
        Posts sorted by final_score descending. Posts without embeddings are
        placed at the end, preserving their original relative order.
    """
    if not user_context or not posts:
        return posts

    try:
        context_vec = np.array(embedding_service.embed(user_context), dtype=np.float32)
    except Exception as exc:
        logger.warning("rank_by_user_context: embed failed, returning original order — %s", exc)
        return posts

    with_score: list[tuple[float, object]] = []
    without_embedding: list = []

    for post in posts:
        if not getattr(post, "embedding", None):
            without_embedding.append(post)
            continue
        try:
            post_vec = np.array(deserialize(post.embedding), dtype=np.float32)
            sim = _cosine_similarity(context_vec, post_vec)
            relevance = float(getattr(post, "relevance_score", 0) or 0)
            final = relevance * relevance_weight + sim * 10 * semantic_weight
            with_score.append((final, post))
        except Exception as exc:
            logger.debug("rank_by_user_context: skipping post %d — %s", getattr(post, "id", "?"), exc)
            without_embedding.append(post)

    with_score.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in with_score] + without_embedding


def semantic_augment_for_briefing(
    existing_posts: list,
    embedding_service: EmbeddingService,
    store,
    n: int = 5,
) -> list:
    """Find posts semantically relevant to AI collaboration techniques,
    excluding those already in existing_posts.

    Used to ensure the daily briefing always includes some ai-technique content
    even when keyword scoring misses it.
    """
    _AI_TECHNIQUE_QUERY = (
        "AI collaboration techniques agentic workflow prompt engineering patterns "
        "claude.md agent memory management practical LLM usage context window "
        "system prompt design multi-agent orchestration"
    )
    try:
        query_embedding = embedding_service.embed(_AI_TECHNIQUE_QUERY)
        exclude_ids = [p.id for p in existing_posts]
        results = vector_search(
            query_embedding, store, top_k=n, exclude_ids=exclude_ids
        )
        return results
    except Exception as exc:
        logger.warning("semantic_augment_for_briefing: failed — %s", exc)
        return []
