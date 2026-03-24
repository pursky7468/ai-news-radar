"""FastAPI dependency providers."""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.store.news_store import NewsStore

_engine = create_engine(settings.database_url)
_SessionLocal = sessionmaker(bind=_engine)


def get_db() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_news_store(db: Session = None) -> NewsStore:
    return NewsStore(session=db)
