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


settings = Settings()
