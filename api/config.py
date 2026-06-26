"""Application configuration loaded from environment variables / .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "sqlite+aiosqlite:///./astroml.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_version: str = "1.0.0"

    # CORS — allow Vite dev server by default
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # ML model paths
    model_path: str = "outputs/model.pkl"
    benchmark_results_dir: str = "benchmark_results"

    # Logging
    log_level: str = "INFO"

    # Distributed Tracing (issue #336)
    tracing_enabled: bool = False
    tracing_exporter: str = "jaeger"  # jaeger|zipkin|console
    tracing_sample_rate: float = 0.1  # 10% sampling by default
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    service_name: str = "astroml-api"

    # Contact form / support tickets (issue #305)
    # Empty reCAPTCHA secret disables spam verification (dev/test default).
    contact_recaptcha_secret: str = ""
    contact_recaptcha_min_score: float = 0.5  # reCAPTCHA v3 score threshold
    # Empty SendGrid key → emails are logged instead of sent (dev/test default).
    sendgrid_api_key: str = ""
    contact_email_from: str = "no-reply@astroml.dev"
    contact_support_email: str = "support@astroml.dev"

    # Feedback collection / GitHub integration (issue #308)
    # When both are set, new feedback opens a GitHub issue in this repo.
    github_token: str = ""
    github_repo: str = ""  # "owner/repo"


settings = Settings()
