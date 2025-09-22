from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


class Settings:
    """Application configuration sourced from environment variables."""

    app_name: str = os.getenv("APP_NAME", "Provider Catalog API")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db:5432/provider_catalog",
    )
    page_size: int = int(os.getenv("PAGE_SIZE", "20"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
