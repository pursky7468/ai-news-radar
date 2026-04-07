"""Digest trigger endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.api.deps import get_db, get_news_store
from app.config import settings
from app.notifier.digest_notifier import DigestNotifier
from app.schemas import DigestTriggerResult

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/api/digest/trigger", response_model=DigestTriggerResult)
def trigger_digest(db: Session = Depends(get_db)):
    store = get_news_store(db)
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
        user_context=settings.user_context,
        highlight_scorer_enabled=settings.FEATURES.get("highlight_scorer", False),
    )
    summary = notifier.run()
    return DigestTriggerResult(**summary)
