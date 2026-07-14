"""Price history + return calculations, backed by yfinance (no API key required)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from app import cache
from app.data.universe import meta_by_ticker, tickers
from app.core.config import settings
from app.services.yahoo_session import session

_NAME_TTL_SECONDS = 24 * 60 * 60


class TickerNotFoundError(Exception):
    pass


def fetch_price_history(ticker: str, period: str = None) -> pd.DataFrame: # type: ignore
    """Daily close prices for `ticker` and the market benchmark, aligned on date.

    Returns a DataFrame indexed by normalized trading-day timestamps with
    columns [ticker, market].
    """
    period = period or settings.default_period
    symbols = [ticker, settings.market_ticker]

    data = yf.download(
        symbols,
        period=period,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        session=session,
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
    """Full company name for `ticker`, falling back to the ticker itself.

    Uses Yahoo's search endpoint rather than `yf.Ticker(...).info`: `.info` hits
    a crumb-protected endpoint that is heavily rate-limited and routinely fails
    from datacenter IPs, which silently degraded every name to the bare ticker.
    """
    symbol = ticker.upper()

    cache_key = f"name:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    name = _search_company_name(symbol) or _universe_company_name(symbol) or symbol
    cache.set(cache_key, name, _NAME_TTL_SECONDS)
    return name


def _search_company_name(symbol: str) -> str | None:
    try:
        resp = session.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": symbol, "quotesCount": 5, "newsCount": 0},
            timeout=10,
        )
        resp.raise_for_status()
        quotes = resp.json().get("quotes") or []
    except Exception:
        return None

    for quote in quotes:
        if (quote.get("symbol") or "").upper() == symbol:
            return quote.get("longname") or quote.get("shortname") or None
    return None


def _universe_company_name(symbol: str) -> str | None:
    """Offline fallback for the tickers we already label by hand."""
    meta = meta_by_ticker().get(symbol)
    return meta.get("name") if meta else None