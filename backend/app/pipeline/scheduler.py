"""APScheduler setup: fetch job (every N min) + digest job (cron)."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def build_scheduler(
    fetch_interval_minutes: int,
    digest_cron: str,
    fetch_pipeline,
    digest_notifier,
) -> BackgroundScheduler:
    sched = BackgroundScheduler()
    sched.add_job(
        fetch_pipeline.run,
        trigger=IntervalTrigger(minutes=fetch_interval_minutes),
        id="fetch_job",
        name="X fetch + score + store",
        replace_existing=True,
    )
    sched.add_job(
        digest_notifier.run,
        trigger=CronTrigger.from_crontab(digest_cron),
        id="digest_job",
        name="Digest notifier",
        replace_existing=True,
    )
    return sched


def start_scheduler() -> None:
    global _scheduler
    from app.config import settings
    from app.api.deps import _SessionLocal
    from app.fetcher.hn_fetcher import HackerNewsFetcher
    from app.fetcher.reddit_fetcher import RedditFetcher
    from app.fetcher.github_fetcher import GitHubFetcher
    from app.fetcher.multi_source_fetcher import MultiSourceFetcher
    from app.notifier.digest_notifier import DigestNotifier
    from app.pipeline.fetch_pipeline import FetchPipeline
    from app.scorer.relevance_scorer import RelevanceScorer
    from app.store.news_store import NewsStore

    db = _SessionLocal()
    store = NewsStore(session=db)
    hn = HackerNewsFetcher(
        keywords=settings.hn_keywords_list,
        fetch_limit=settings.hn_fetch_limit,
        news_store=store,
    )
    reddit = RedditFetcher(
        subreddits=settings.reddit_subreddits_list,
        keywords=settings.reddit_keywords_list,
        fetch_limit=settings.reddit_fetch_limit,
        news_store=store,
    )
    github = GitHubFetcher(
        keywords=settings.github_keywords_list,
        monitored_repos=settings.github_monitored_repos_list,
        fetch_limit=settings.github_fetch_limit,
        github_token=settings.github_token,
        news_store=store,
    )
    fetcher = MultiSourceFetcher(hn=hn, reddit=reddit, github=github)
    scorer = RelevanceScorer(
        news_store=store,
        keywords_config_path=settings.keywords_config_path,
        threshold=settings.relevance_threshold,
    )
    pipeline = FetchPipeline(
        news_store=store,
        fetcher=fetcher,
        scorer=scorer,
    )
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
    _scheduler = build_scheduler(
        fetch_interval_minutes=settings.fetch_interval_minutes,
        digest_cron=settings.digest_cron,
        fetch_pipeline=pipeline,
        digest_notifier=notifier,
    )
    _scheduler.start()
    logger.info("Scheduler started (fetch every %dmin, digest: %s)", settings.fetch_interval_minutes, settings.digest_cron)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
