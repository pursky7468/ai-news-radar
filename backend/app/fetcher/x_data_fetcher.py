"""XDataFetcher: fetch posts from X API v2 via Tweepy."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import tweepy

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_TWEET_FIELDS = ["author_id", "created_at", "text"]
_EXPANSIONS = ["author_id"]
_USER_FIELDS = ["username"]


class XDataFetcher:
    def __init__(
        self,
        bearer_token: str,
        news_store=None,
        _client=None,  # injected in tests
    ) -> None:
        self._store = news_store
        self._client = _client or tweepy.Client(
            bearer_token=bearer_token,
            wait_on_rate_limit=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 100,
    ) -> list[dict]:
        query = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords)
        query += " -is:retweet lang:en"
        return self._paginate_search(query, max_results=max_results)

    def fetch_from_accounts(
        self,
        handles: list[str],
        max_results: int = 50,
    ) -> list[dict]:
        results: list[dict] = []
        for handle in handles:
            user_resp = self._client.get_user(username=handle)
            if not user_resp.data:
                logger.warning("Account @%s not found, skipping", handle)
                continue
            user_id = user_resp.data.id
            posts = self._paginate_timeline(user_id, max_results=max_results)
            results.extend(posts)
        return results

    # ------------------------------------------------------------------
    # Pagination helpers
    # ------------------------------------------------------------------

    def _paginate_search(self, query: str, max_results: int) -> list[dict]:
        collected: list[dict] = []
        next_token: Optional[str] = None
        retries = 0

        while len(collected) < max_results:
            page_size = min(10, max_results - len(collected))
            try:
                resp = self._client.search_recent_tweets(
                    query=query,
                    max_results=max(10, page_size),
                    tweet_fields=_TWEET_FIELDS,
                    pagination_token=next_token,
                )
                retries = 0
            except tweepy.errors.TooManyRequests as exc:
                retries += 1
                if retries >= _MAX_RETRIES:
                    logger.error("Rate limit exceeded after %d retries, skipping query", _MAX_RETRIES)
                    break
                reset_ts = int(getattr(exc.response, "headers", {}).get("x-rate-limit-reset", 0))
                wait = max(0, reset_ts - int(time.time()))
                logger.warning("Rate limited — waiting %ds (attempt %d/%d)", wait, retries, _MAX_RETRIES)
                time.sleep(wait or 1)
                continue

            tweets = resp.data or []
            for tweet in tweets:
                post = self._tweet_to_dict(tweet)
                collected.append(post)

            next_token = resp.meta.next_token if resp.meta else None
            if not next_token:
                break

        return self._deduplicate(collected)

    def _paginate_timeline(self, user_id: str, max_results: int) -> list[dict]:
        collected: list[dict] = []
        next_token: Optional[str] = None

        while len(collected) < max_results:
            resp = self._client.get_users_tweets(
                id=user_id,
                max_results=min(100, max_results - len(collected)),
                tweet_fields=_TWEET_FIELDS,
                pagination_token=next_token,
            )
            tweets = resp.data or []
            for tweet in tweets:
                collected.append(self._tweet_to_dict(tweet))

            next_token = resp.meta.next_token if resp.meta else None
            if not next_token:
                break

        return self._deduplicate(collected)

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(self, posts: list[dict]) -> list[dict]:
        if not self._store:
            return posts
        return [p for p in posts if not self._store.get_post_by_id_by_x(p["x_post_id"])]

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _tweet_to_dict(tweet) -> dict:
        tweet_id = str(tweet.id)
        return {
            "x_post_id": tweet_id,
            "author_handle": str(getattr(tweet, "author_id", "unknown")),
            "content": tweet.text or "",
            "url": f"https://x.com/i/web/status/{tweet_id}",
            "posted_at": getattr(tweet, "created_at", None) or datetime.now(timezone.utc),
        }
