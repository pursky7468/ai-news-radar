"""Summary API routes — GET /api/summary/latest."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.api.deps import get_db, get_news_store
from app.schemas import ReportResponse

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/api/summary/latest", response_model=ReportResponse)
def get_latest_summary(db: Session = Depends(get_db)):
    """Return the most recently generated zh-TW report."""
    store = get_news_store(db)
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No report available yet")
    return report
