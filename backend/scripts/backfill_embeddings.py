"""Backfill embeddings for all posts that don't have one yet.

Usage (run from backend/ directory):
    python scripts/backfill_embeddings.py [--batch-size 50] [--limit 0]

Options:
    --batch-size N   Posts per commit batch (default: 50)
    --limit N        Maximum total posts to process; 0 = all (default: 0)
    --dry-run        Count posts without computing embeddings

Requires FEATURE_EMBEDDINGS=true in .env (or pass --force to bypass).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Resolve backend package
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))
os.chdir(_BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill post embeddings")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=0, help="0 = all posts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Run even if FEATURE_EMBEDDINGS=false")
    args = parser.parse_args()

    from app.config import settings
    from app.embeddings.embedding_service import EmbeddingService, serialize
    from app.models import Base
    from app.store.news_store import NewsStore
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    if not settings.FEATURES.get("embeddings") and not args.force:
        logger.error(
            "FEATURE_EMBEDDINGS is not enabled. "
            "Set FEATURE_EMBEDDINGS=true in .env or use --force."
        )
        sys.exit(1)

    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        store = NewsStore(session=db)

        # Count
        total_without = store.get_posts_without_embedding(limit=10000)
        n_total = len(total_without)
        logger.info("Posts without embedding: %d", n_total)

        if args.dry_run:
            logger.info("Dry run — exiting without computing embeddings.")
            return

        if n_total == 0:
            logger.info("All posts already have embeddings. Nothing to do.")
            return

        to_process = total_without if args.limit == 0 else total_without[: args.limit]
        logger.info("Will process %d posts (batch_size=%d)", len(to_process), args.batch_size)

        svc = EmbeddingService(
            model_name=settings.embedding_model,
            use_local=not bool(settings.hf_api_token),
            hf_api_token=settings.hf_api_token,
        )
        svc.warmup()

        success = 0
        failed = 0
        batch = []

        for i, post in enumerate(to_process, 1):
            try:
                embedding = svc.embed_text_for_post(post)
                store.update_post_embedding(post.id, serialize(embedding))
                success += 1
                batch.append(post.id)
            except Exception as exc:
                logger.warning("Failed post %d: %s", post.id, exc)
                failed += 1

            if len(batch) >= args.batch_size:
                store.commit()
                logger.info("Progress: %d/%d (success=%d, failed=%d)", i, len(to_process), success, failed)
                batch = []
                time.sleep(0.05)  # brief pause to avoid sustained CPU load

        if batch:
            store.commit()

        logger.info("Done. success=%d, failed=%d", success, failed)


if __name__ == "__main__":
    main()
