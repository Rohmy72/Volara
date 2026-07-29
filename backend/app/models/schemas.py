"""Response models for the analysis API."""
from __future__ import annotations

from pydantic import BaseModel


class Verdict(BaseModel):
    label: str
    explanation: str
    news_reaction_ratio: float | None
    n_news_days: int
    n_quiet_days: int
    top_moves_explained_pct: float | None
    # Directional bias — which way news-day moves lean. News Beta measures the
    # size of news-day moves; these describe their sign.
    direction_label: str | None = None
    direction_explanation: str | None = None
    news_day_up_share: float | None = None
    n_news_up_days: int = 0
    n_news_down_days: int = 0
    news_day_avg_signed_pct: float | None = None
    avg_up_move_pct: float | None = None
    avg_down_move_pct: float | None = None


class PricePoint(BaseModel):
    date: str
    close: float
    daily_return: float | None
    abnormal_return: float | None
    is_news_day: bool


class BuzzwordOut(BaseModel):
    word: str
    lift: float
    occurrences: int
    avg_move_pct: float
    example_headline: str


class NewsItemOut(BaseModel):
    title: str
    source: str
    url: str
    published_at: str
    summary: str
    sentiment_score: float | None
    matched_trading_day: str | None


class AnalysisResponse(BaseModel):
    ticker: str
    company_name: str
    market_benchmark: str
    period: str
    verdict: Verdict
    price_series: list[PricePoint]
    buzzwords: list[BuzzwordOut]
    news: list[NewsItemOut]
