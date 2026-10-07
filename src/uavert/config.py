"""Settings, read from environment variables (and `.env` in development)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None

    region_code: str = "CA-ON-TOR"
    csi_edition: str = "2009"

    http_timeout_s: float = 10.0
    http_retries: int = 2
    # Identifies the app to outside services (Nominatim requires this). No personal contact details.
    user_agent: str = "uavert-demo/0.1"

    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osrm_url: str = "https://routing.openstreetmap.de/routed-foot"
    cbc_rss_url: str = "https://www.cbc.ca/webfeed/rss/rss-canada-toronto"
    gdelt_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"

    # Database connections per app instance (hosted functions use a small number).
    db_pool_max: int = Field(5, ge=1, validation_alias="DB_POOL_MAX")

    # Request limit for endpoints that call outside services, per client IP.
    outside_calls_per_minute: int = 30

    # Background refresh of the live sources while the app runs (0 = off; `uavert serve` defaults to 30).
    refresh_minutes: int = Field(0, ge=0, validation_alias="UAVERT_REFRESH_MINUTES")


@lru_cache
def get_settings() -> Settings:
    return Settings()
