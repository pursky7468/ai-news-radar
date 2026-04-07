"""MultiSourceFetcher: orchestrates HN, Reddit, and GitHub adapters."""
from __future__ import annotations

import logging

from app.fetcher.hn_fetcher import HackerNewsFetcher
from app.fetcher.reddit_fetcher import RedditFetcher
from app.fetcher.github_fetcher import GitHubFetcher
from app.fetcher.source_post import SourcePost

logger = logging.getLogger(__name__)


class MultiSourceFetcher:
    def __init__(
        self,
        hn: HackerNewsFetcher,
        reddit: RedditFetcher,
        github: GitHubFetcher,
        arxiv=None,  # Optional[ArxivFetcher] — injected when feature flag enabled
    ) -> None:
        self._adapters = [hn, reddit, github]
        if arxiv is not None:
            self._adapters.append(arxiv)

    def fetch(self) -> list[SourcePost]:
        results: list[SourcePost] = []
        for adapter in self._adapters:
            name = adapter.__class__.__name__
            try:
                posts = adapter.fetch()
                logger.info("%s: fetched %d posts", name, len(posts))
                results.extend(posts)
            except Exception as exc:
                logger.error("%s: fetch failed, skipping: %s", name, exc)
        return results
