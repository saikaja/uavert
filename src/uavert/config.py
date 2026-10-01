"""Settings, read from environment variables (and `.env` in development)."""

from functools import lru_cache
from pathlib import Path

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
    user_agent: str = "uavert-demo/0.1 (contact: saikaja99@gmail.com)"

    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osrm_url: str = "https://routing.openstreetmap.de/routed-foot"
    cbc_rss_url: str = "https://www.cbc.ca/webfeed/rss/rss-canada-toronto"
    gdelt_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"

    # Request limit for endpoints that call outside services, per client IP.
    outside_calls_per_minute: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
