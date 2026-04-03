"""DigestNotifier: generate and deliver periodic AI news digests."""
from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
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
        gemini_api_key: str = "",
        gemini_model: str = "gemini-2.0-flash",
    ) -> None:
        self._store = news_store
        self._smtp = smtp_config
        self._webhook_url = webhook_url
        self._top_n = top_n
        self._gemini_api_key = gemini_api_key
        self._gemini_model = gemini_model

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> dict:
        posts = self.generate_digest()
        if not posts:
            return {"posts_included": 0, "email_sent": False, "webhook_sent": False}

        # AI summarization — optional, gated by GEMINI_API_KEY
        report_markdown: Optional[str] = None
        if self._gemini_api_key:
            report_markdown = self._run_summarization(posts)

        email_ok = self.send_email(posts, report_markdown) if self._smtp else False
        webhook_ok = self.send_webhook(posts, report_markdown) if self._webhook_url else False

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

    def _run_summarization(self, posts: list[Post]) -> Optional[str]:
        """Run Gemini summarization and assemble report. Returns Markdown or None on total failure."""
        try:
            from app.summarizer.gemini_client import GeminiClient
            from app.summarizer.summary_generator import SummaryGenerator

            client = GeminiClient(self._gemini_api_key, self._gemini_model)
            generator = SummaryGenerator(client, self._store)
            generator.summarize_batch(posts)

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # Refresh posts from session to pick up summary_zh values
            refreshed = [self._store.get_post_by_id(p.id) or p for p in posts]
            report_content = generator.assemble_report(refreshed, today)

            if report_content:
                self._store.save_report(
                    content=report_content,
                    post_count=len(posts),
                    model_used=self._gemini_model,
                )
            return report_content or None
        except Exception as exc:
            logger.error("Summarization pipeline failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Digest generation
    # ------------------------------------------------------------------

    def generate_digest(self) -> list[Post]:
        return self._store.get_unsent_relevant_posts(limit=self._top_n)

    # ------------------------------------------------------------------
    # Email delivery
    # ------------------------------------------------------------------

    def send_email(self, posts: list[Post], report_markdown: Optional[str] = None) -> bool:
        if not self._smtp:
            return False
        try:
            html = _render_email_html(posts, report_markdown)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"AI News Digest — {len(posts)} posts"
            msg["From"] = self._smtp["from"]
            msg["To"] = self._smtp["to"]
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self._smtp["host"], self._smtp["port"]) as server:
                server.starttls()
                server.login(self._smtp["user"], self._smtp["password"])
                server.send_message(msg)

            return True
        except Exception as exc:
            logger.error("Email delivery failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Webhook delivery
    # ------------------------------------------------------------------

    def send_webhook(self, posts: list[Post], report_markdown: Optional[str] = None) -> bool:
        if not self._webhook_url:
            return True  # not configured — no-op
        try:
            payload = {
                "digest": [
                    {
                        "source": p.source,
                        "external_id": p.external_id,
                        "author": p.author_handle,
                        "content": p.content,
                        "url": p.url,
                        "score": p.relevance_score,
                        "labels": p.labels,
                        "summary_zh": p.summary_zh,
                    }
                    for p in posts
                ],
                "report_markdown": report_markdown,
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

def _render_email_html(posts: list[Post], report_markdown: Optional[str] = None) -> str:
    rows = "\n".join(
        f"""
        <tr>
          <td style="padding:8px 0; border-bottom:1px solid #eee;">
            <a href="{p.url}" style="font-weight:bold;">{p.author_handle}</a>
            <span style="color:#888; margin-left:8px;">score: {p.relevance_score:.1f}</span>
            <span style="color:#555; margin-left:8px;">{', '.join(p.labels or [])}</span>
            <p style="margin:4px 0 0;">{p.content[:280]}</p>
            {f'<p style="margin:4px 0 0; color:#333;"><em>{p.summary_zh}</em></p>' if p.summary_zh else ""}
          </td>
        </tr>
        """
        for p in posts
    )
    summary_section = ""
    if report_markdown:
        summary_section = f"""
        <hr style="margin:24px 0;">
        <h2>中文摘要</h2>
        <pre style="white-space:pre-wrap; font-family:sans-serif; font-size:14px;">{report_markdown}</pre>
        """
    return f"""
    <html><body>
    <h2>AI News Digest — {len(posts)} posts</h2>
    <table style="width:100%; font-family:sans-serif; font-size:14px;">
      {rows}
    </table>
    {summary_section}
    </body></html>
    """
