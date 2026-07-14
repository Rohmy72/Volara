"""Price history + return calculations, backed by yfinance (no API key required)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf
import requests

from app.data.universe import tickers
from app.core.config import settings

# 1. Create the session with the browser User-Agent header
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
})


class TickerNotFoundError(Exception):
    pass


def fetch_price_history(ticker: str, period: str = None) -> pd.DataFrame: # type: ignore
    """Daily close prices for `ticker` and the market benchmark, aligned on date.

    Returns a DataFrame indexed by normalized trading-day timestamps with
    columns [ticker, market].
    """
    period = period or settings.default_period
    symbols = [ticker, settings.market_ticker]

    # 2. Added session=session to yf.download to stop Render from being blocked!
    data = yf.download(
        symbols, 
        period=period, 
        auto_adjust=True, 
        progress=False, 
        group_by="ticker",
        session=session
    )

    if data.empty:
        raise TickerNotFoundError(f"No price data returned for '{ticker}'")

    def _extract_close(sym: str) -> pd.Series:
        try:
            series = data[sym]["Close"]
        except KeyError:
            # yfinance collapses to a flat frame when only one symbol resolves
            if "Close" in data.columns:
                series = data["Close"]
            else:
                raise TickerNotFoundError(f"No price data returned for '{sym}'")
        return series.dropna()

    ticker_close = _extract_close(ticker)
    market_close = _extract_close(settings.market_ticker)

    if ticker_close.empty:
        raise TickerNotFoundError(f"'{ticker}' did not resolve to any price history")

    df = pd.concat(
        [ticker_close.rename("ticker"), market_close.rename("market")], axis=1
    ).dropna()
    df.index = df.index.normalize() # type: ignore
    return df


def compute_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    """Simple daily percentage returns for both columns."""
    return price_df.pct_change().dropna(how="all")


def get_company_name(ticker: str) -> str:
    try:
        # 3. Added session=session to the individual Ticker call here too!
        info = yf.Ticker(ticker, session=session).info
        return info.get("longName") or info.get("shortName") or ticker.upper()
    except Exception:
        return ticker.upper()