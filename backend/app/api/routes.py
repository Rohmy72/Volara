from __future__ import annotations

import re

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app import cache
from app.core.config import settings
from app.models.schemas import (
    AnalysisResponse,
    BuzzwordOut,
    NewsItemOut,
    PricePoint,
    Verdict,
)
from app.services import leaderboard, market_data, news_beta, news_sources
from app.services.buzzwords import extract_buzzwords
from app.services.leaderboard import LeaderboardUnavailable
from app.services.market_data import TickerNotFoundError

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/leaderboard")
def get_leaderboard():
    """Precomputed leaderboards: stocks ranked by News Reaction Ratio (with
    sector tags for client-side filtering) and trending buzzwords bucketed into
    week / month / year windows. Served from a snapshot on disk."""
    try:
        return leaderboard.load_snapshot()
    except LeaderboardUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/analyze/{ticker}", response_model=AnalysisResponse)
def analyze(
    ticker: str,
    period: str = Query(
        default=None,
        description="yfinance period string, e.g. 6mo, 1y, 2y",
    ),
):
    ticker = ticker.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    period = period or settings.default_period
    cache_key = f"{ticker}:{period}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        price_df = market_data.fetch_price_history(ticker, period)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch price data: {e}")

    returns = market_data.compute_returns(price_df)
    if len(returns) < settings.min_quiet_days:
        raise HTTPException(
            status_code=422,
            detail="Not enough price history in this window to run an analysis.",
        )

    company_name = market_data.get_company_name(ticker)

    try:
        news_items = news_sources.fetch_all_news(ticker, company_name)
    except Exception:
        news_items = []

    result = news_beta.run_news_beta_analysis(
        returns,
        news_items,
        min_news_days=settings.min_news_days,
        min_quiet_days=settings.min_quiet_days,
        window_days=settings.news_alignment_window_days,
    )

    buzzwords = extract_buzzwords(
        result.news_day_map, result.abnormal_returns, ticker, company_name
    )

    news_days = set(result.news_day_map.keys())
    price_series = []
    for date, row in price_df.iterrows():
        daily_ret = returns["ticker"].get(date)
        abnormal = result.abnormal_returns.get(date)
        price_series.append(
            PricePoint(
                date=date.strftime("%Y-%m-%d"), # type: ignore
                close=round(float(row["ticker"]), 4),
                daily_return=round(float(daily_ret), 6) if pd.notna(daily_ret) else None,
                abnormal_return=round(float(abnormal), 6) if pd.notna(abnormal) else None,
                is_news_day=date in news_days,
            )
        )

    # Reverse-map each news item's title to the trading day it was aligned to,
    # so the UI can show "this article lined up with a +4.2% move" etc.
    title_to_day = {}
    for day, items in result.news_day_map.items():
        for item in items:
            title_to_day[item.title] = day.strftime("%Y-%m-%d")

    news_out = [
        NewsItemOut(
            title=item.title,
            source=item.source,
            url=item.url,
            published_at=item.published_at.isoformat(),
            summary=item.summary,
            sentiment_score=item.sentiment_score,
            matched_trading_day=title_to_day.get(item.title),
        )
        for item in news_items[:60]
    ]

    response = AnalysisResponse(
        ticker=ticker,
        company_name=company_name,
        market_benchmark=settings.market_ticker,
        period=period,
        verdict=Verdict(
            label=result.verdict_label,
            explanation=result.verdict_explanation,
            news_reaction_ratio=result.nrr,
            n_news_days=result.n_news_days,
            n_quiet_days=result.n_quiet_days,
            top_moves_explained_pct=result.top_moves_explained_pct,
        ),
        price_series=price_series,
        buzzwords=[BuzzwordOut(**vars(b)) for b in buzzwords],
        news=news_out,
    )

    cache.set(cache_key, response, settings.cache_ttl_seconds)
    return response
