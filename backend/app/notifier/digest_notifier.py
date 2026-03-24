"""DigestNotifier: generate and deliver periodic AI news digests."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.models import Post

logger = logging.getLogger(__name__)


class DigestNotifier:
    def __init__(
        self,
        news_store,
        smtp_config: Optional[dict],
        webhook_url: Optional[str],
        top_n: int = 20,
    ) -> None:
        self._store = news_store
        self._smtp = smtp_config
        self._webhook_url = webhook_url
        self._top_n = top_n

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> dict:
        posts = self.generate_digest()
        if not posts:
            return {"posts_included": 0, "email_sent": False, "webhook_sent": False}

        email_ok = self.send_email(posts) if self._smtp else False
        webhook_ok = self.send_webhook(posts) if self._webhook_url else False

        # Mark sent only when ALL configured channels succeed
        configured_channels = []
        if self._smtp:
            configured_channels.append(email_ok)
        if self._webhook_url:
            configured_channels.append(webhook_ok)

        all_ok = all(configured_channels) if configured_channels else True
        if all_ok and posts:
            self._store.mark_digest_sent([p.id for p in posts])

        return {
            "posts_included": len(posts),
            "email_sent": email_ok,
            "webhook_sent": webhook_ok,
        }

    # ------------------------------------------------------------------
    # Digest generation
    # ------------------------------------------------------------------

    def generate_digest(self) -> list[Post]:
        return self._store.get_unsent_relevant_posts(limit=self._top_n)

    # ------------------------------------------------------------------
    # Email delivery
    # ------------------------------------------------------------------

    def send_email(self, posts: list[Post]) -> bool:
        if not self._smtp:
            return False
        try:
            html = _render_email_html(posts)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"AI News Digest — {len(posts)} posts"
            msg["From"] = self._smtp["from"]
            msg["To"] = self._smtp["to"]
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self._smtp["host"], self._smtp["port"]) as server:
                server.starttls()
                server.login(self._smtp["user"], self._smtp["password"])
                server.send_message(msg)

            self._store.mark_digest_sent([p.id for p in posts])
            return True
        except Exception as exc:
            logger.error("Email delivery failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Webhook delivery
    # ------------------------------------------------------------------

    def send_webhook(self, posts: list[Post]) -> bool:
        if not self._webhook_url:
            return True  # not configured — no-op
        try:
            payload = {
                "digest": [
                    {
                        "x_post_id": p.x_post_id,
                        "author": p.author_handle,
                        "content": p.content,
                        "url": p.url,
                        "score": p.relevance_score,
                        "labels": p.labels,
                    }
                    for p in posts
                ]
            }
            resp = httpx.post(self._webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Webhook delivery failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# HTML email template
# ---------------------------------------------------------------------------

def _render_email_html(posts: list[Post]) -> str:
    rows = "\n".join(
        f"""
        <tr>
          <td style="padding:8px 0; border-bottom:1px solid #eee;">
            <a href="{p.url}" style="font-weight:bold;">{p.author_handle}</a>
            <span style="color:#888; margin-left:8px;">score: {p.relevance_score:.1f}</span>
            <span style="color:#555; margin-left:8px;">{', '.join(p.labels or [])}</span>
            <p style="margin:4px 0 0;">{p.content[:280]}</p>
          </td>
        </tr>
        """
        for p in posts
    )
    return f"""
    <html><body>
    <h2>AI News Digest — {len(posts)} posts</h2>
    <table style="width:100%; font-family:sans-serif; font-size:14px;">
      {rows}
    </table>
    </body></html>
    """
