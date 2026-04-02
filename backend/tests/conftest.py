"""Shared test fixtures."""
from datetime import datetime, timezone

import factory
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Post
from app.store.news_store import NewsStore


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine for the test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    """Transactional session rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def news_store(db_session):
    """NewsStore backed by the test session."""
    return NewsStore(session=db_session)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class PostFactory(factory.Factory):
    class Meta:
        model = dict  # produce plain dicts (not ORM objects)

    source = "hackernews"
    external_id = factory.Sequence(lambda n: f"post_{n}")
    author_handle = factory.Sequence(lambda n: f"user_{n}")
    content = factory.Faker("sentence", nb_words=12)
    url = factory.LazyAttribute(lambda o: f"https://news.ycombinator.com/item?id={o.external_id}")
    posted_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    relevance_score = None
    points = None
    is_relevant = False
    labels = factory.LazyFunction(list)
    digest_sent = False


@pytest.fixture
def post_factory():
    return PostFactory
