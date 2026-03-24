"""Health check endpoint."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_news_store
from app.schemas import HealthResponse
from app.store.news_store import NewsStore

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    store = get_news_store(db)
    db_ok = store.check_db_alive()
    last_fetch = store.get_last_fetch_at()
    if db_ok:
        return HealthResponse(status="ok", db="connected", last_fetch_at=last_fetch)
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "db": "disconnected", "last_fetch_at": None},
    )
