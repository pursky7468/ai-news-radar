"""Application configuration loaded from environment variables."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite:///./dev.db"

    # API auth
    api_key: str = "changeme"

    # X API
    x_bearer_token: str = ""
    monitored_accounts: str = "AnthropicAI,OpenAI,LangChainAI"

    # Scheduler
    fetch_interval_minutes: int = 15
    digest_cron: str = "0 8 * * *"

    # Scoring
    relevance_threshold: float = 5.0
    keywords_config_path: Optional[str] = None

    # SMTP
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    digest_email_from: Optional[str] = None
    digest_email_to: Optional[str] = None

    # Webhook
    digest_webhook_url: Optional[str] = None

    @property
    def smtp_config(self) -> Optional[dict]:
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.digest_email_from, self.digest_email_to]):
            return None
        return {
            "host": self.smtp_host,
            "port": self.smtp_port,
            "user": self.smtp_user,
            "password": self.smtp_password,
            "from": self.digest_email_from,
            "to": self.digest_email_to,
        }

    @property
    def monitored_accounts_list(self) -> list[str]:
        return [a.strip() for a in self.monitored_accounts.split(",") if a.strip()]


settings = Settings()
