"""Summary API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.auth import require_api_key
from app.api.deps import get_db, get_news_store
from app.schemas import ReportListItem, ReportResponse

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/api/summary/latest", response_model=ReportResponse)
def get_latest_summary(db: Session = Depends(get_db)):
    """Return the most recently generated zh-TW report."""
    store = get_news_store(db)
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No report available yet")
    return report


@router.get("/api/summary/reports", response_model=List[ReportListItem])
def list_reports(db: Session = Depends(get_db)):
    """Return all reports ordered by generated_at descending (no content)."""
    store = get_news_store(db)
    return store.get_reports()


@router.get("/api/summary/reports/{report_id}", response_model=ReportResponse)
def get_report_by_id(report_id: int, db: Session = Depends(get_db)):
    """Return a specific report by ID including full content."""
    store = get_news_store(db)
    report = store.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
