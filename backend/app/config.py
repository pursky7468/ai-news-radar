"""Application configuration loaded from environment variables."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite:///./dev.db"

    # API auth
    api_key: str = "changeme"

    # Hacker News
    hn_keywords: str = "ai agent,LLM,RAG,MCP,multi-agent,AutoGen,LangChain"
    hn_fetch_limit: int = 100

    # Reddit
    reddit_subreddits: str = "MachineLearning,LocalLLaMA,singularity,artificial"
    reddit_keywords: str = ""
    reddit_fetch_limit: int = 100

    # GitHub
    github_monitored_repos: str = "langchain-ai/langchain,microsoft/autogen,ollama/ollama,ggerganov/llama.cpp"
    github_keywords: str = "ai agent,llm,rag"
    github_fetch_limit: int = 30
    github_token: str = ""

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

    # Gemini AI Summarizer (optional — disabled if api key absent)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    summary_post_limit: int = 20

    @property
    def hn_keywords_list(self) -> list[str]:
        return [k.strip() for k in self.hn_keywords.split(",") if k.strip()]

    @property
    def reddit_subreddits_list(self) -> list[str]:
        return [s.strip() for s in self.reddit_subreddits.split(",") if s.strip()]

    @property
    def reddit_keywords_list(self) -> list[str]:
        return [k.strip() for k in self.reddit_keywords.split(",") if k.strip()]

    @property
    def github_monitored_repos_list(self) -> list[str]:
        return [r.strip() for r in self.github_monitored_repos.split(",") if r.strip()]

    @property
    def github_keywords_list(self) -> list[str]:
        return [k.strip() for k in self.github_keywords.split(",") if k.strip()]

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



settings = Settings()
