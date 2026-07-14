"""Environment-driven configuration. No secrets are hard-coded here."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Optional: enables the Alpha Vantage NEWS_SENTIMENT feed as a bonus source.
    # The app works fine without it, using only free/keyless sources.
    alpha_vantage_key: str | None = os.environ.get("AV_KEY") or None

    market_ticker: str = os.environ.get("MARKET_TICKER", "SPY")
    default_period: str = os.environ.get("ANALYSIS_PERIOD", "1y")

    min_news_days: int = int(os.environ.get("MIN_NEWS_DAYS", "5"))
    min_quiet_days: int = int(os.environ.get("MIN_QUIET_DAYS", "20"))

    # Trading-day window (+/- days) used to align a news article's
    # publish timestamp to the nearest market session.
    news_alignment_window_days: int = 1

    cache_ttl_seconds: int = int(os.environ.get("CACHE_TTL_SECONDS", "1800"))

    cors_origins: list[str] = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")


settings = Settings()
