"""Bookmark CRUD endpoints (Phase 19).

Controlled by FEATURES["bookmarks"] — router is only registered when flag is True.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.api.deps import get_db, get_news_store
from app.schemas import BookmarkCreate, BookmarkResponse

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/api/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: BookmarkCreate, db: Session = Depends(get_db)):
    store = get_news_store(db)
    try:
        bm = store.add_bookmark(article_id=payload.article_id, note=payload.note or "")
        store.commit()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    except LookupError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Article already bookmarked")
    # Reload with relationship
    from app.models import Bookmark
    bm = db.get(Bookmark, bm.id)
    return bm


@router.get("/api/bookmarks", response_model=list[BookmarkResponse])
def list_bookmarks(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    store = get_news_store(db)
    bookmarks = store.get_bookmarks(q=q)
    return bookmarks


@router.delete("/api/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    store = get_news_store(db)
    deleted = store.delete_bookmark(bookmark_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    store.commit()
