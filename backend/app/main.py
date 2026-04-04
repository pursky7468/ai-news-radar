"""FastAPI application entrypoint."""
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import digest, health, news, summary


def _catchup_digest() -> None:
    """Run a digest in a background thread if no report exists in the last 23 hours."""
    try:
        from app.config import settings
        from app.api.deps import _SessionLocal
        from app.store.news_store import NewsStore
        from app.notifier.digest_notifier import DigestNotifier

        db = _SessionLocal()
        store = NewsStore(session=db)
        latest = store.get_latest_report()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=23)

        if latest is None or latest.generated_at.replace(tzinfo=timezone.utc) < cutoff:
            notifier = DigestNotifier(
                news_store=store,
                smtp_config=settings.smtp_config,
                webhook_url=settings.digest_webhook_url,
                gemini_api_key=settings.gemini_api_key,
                gemini_model=settings.gemini_model,
                groq_api_key=settings.groq_api_key,
                groq_model=settings.groq_model,
                lookback_hours=settings.digest_lookback_hours,
                briefings_output_dir=settings.briefings_output_dir or None,
            )
            notifier.run()
        db.close()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Startup catch-up digest failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.pipeline.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    threading.Thread(target=_catchup_digest, daemon=True).start()
    yield
    stop_scheduler()


app = FastAPI(title="X AI News Researcher", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(digest.router)
app.include_router(summary.router)
