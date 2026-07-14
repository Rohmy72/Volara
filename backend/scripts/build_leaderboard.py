"""Precompute the leaderboard snapshot the web app serves.

Runs the same market-model NRR analysis used for single-ticker requests across
the whole sector-tagged universe, plus a cross-stock "trending buzzwords"
aggregation bucketed into last-week / last-month / last-year windows. Writes
the result to backend/app/data/leaderboard.json, which the API serves as-is.

Usage (from the backend/ directory):

    python3 scripts/build_leaderboard.py

Re-run it on a schedule (cron, GitHub Action, etc.) to keep the boards fresh.
Uses only free data sources (yfinance + Google/Yahoo RSS); Alpha Vantage is
intentionally skipped here to avoid its 25-requests/day free-tier cap.

NOTE on the buzzword windows: free RSS feeds only expose recent articles, so
the "year" window is naturally sparse — it can only include as much history as
the free feeds still carry. The windowing logic is correct; the data density
is a limitation of free sources, not a bug.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

# Make `app` importable when run as a script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.universe import MARKET_TICKER, UNIVERSE, meta_by_ticker, tickers
from app.services import news_beta, news_sources
from app.services.buzzwords import _ALWAYS_EXCLUDE, _tokenize
from app.services.yahoo_session import session

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "leaderboard.json"

PERIOD = "1y"
MIN_NEWS_DAYS = 4
MIN_QUIET_DAYS = 20
WINDOWS = {"week": 7, "month": 30, "year": 365}
MAX_BUZZWORDS_PER_WINDOW = 18
MAX_WORKERS = 6


def fetch_all_prices(symbols: list[str]) -> pd.DataFrame:
    """One batched download for the whole universe + market benchmark."""
    data = yf.download(
        symbols,
        period=PERIOD,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        session=session,
    )
    closes = {}
    for sym in symbols:
        try:
            series = data[sym]["Close"].dropna()
        except (KeyError, TypeError):
            continue
        if len(series) > 100:
            closes[sym] = series
    if not closes:
        raise RuntimeError(
            f"Yahoo returned no usable price history for any of the {len(symbols)} "
            "universe symbols — refusing to overwrite the leaderboard with an empty snapshot."
        )
    df = pd.DataFrame(closes)
    df.index = df.index.normalize()
    return df


def analyze_one(ticker: str, meta: dict, price_df: pd.DataFrame):
    """Return (stock_entry | None, list_of_buzzword_events)."""
    if ticker not in price_df.columns or MARKET_TICKER not in price_df.columns:
        return None, []

    returns = (
        price_df[[ticker, MARKET_TICKER]]
        .rename(columns={ticker: "ticker", MARKET_TICKER: "market"})
        .pct_change()
        .dropna(how="all")
    )
    if len(returns) < MIN_QUIET_DAYS:
        return None, []

    name = meta["name"]
    try:
        news_items = news_sources.fetch_all_news(ticker, name)
    except Exception:
        news_items = []

    result = news_beta.run_news_beta_analysis(
        returns,
        news_items,
        min_news_days=MIN_NEWS_DAYS,
        min_quiet_days=MIN_QUIET_DAYS,
        window_days=1,
    )

    entry = None
    if result.status == "ok" and result.nrr is not None:
        entry = {
            "ticker": ticker,
            "name": name,
            "sector": meta["sector"],
            "nrr": result.nrr,
            "verdict_label": result.verdict_label,
            "n_news_days": result.n_news_days,
        }

    # Collect (word, published_at, move, headline, ticker, day) events for the
    # cross-stock trending-buzzword aggregation.
    exclude = set(_ALWAYS_EXCLUDE) | {ticker.lower()} | _tokenize(name)
    abn = result.abnormal_returns
    events = []
    for day, items in result.news_day_map.items():
        if day not in abn.index:
            continue
        move = abs(float(abn.loc[day]))
        if pd.isna(move):
            continue
        for item in items:
            tokens = (_tokenize(item.title) | _tokenize(item.summary)) - exclude
            for tok in tokens:
                events.append(
                    {
                        "word": tok,
                        "published_at": item.published_at,
                        "move": move,
                        "headline": item.title,
                        "ticker": ticker,
                        "day": day,
                    }
                )
    return entry, events


def trending_for_window(events: list[dict], days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    windowed = [
        e for e in events if pd.Timestamp(e["published_at"]).tz_convert("UTC") >= cutoff
    ] if events else []
    if not windowed:
        return []

    baseline = sum(e["move"] for e in windowed) / len(windowed)
    if baseline <= 0:
        return []

    # Dedupe so each (ticker, trading-day) contributes at most once per word.
    per_word: dict[str, dict] = {}
    for e in windowed:
        w = e["word"]
        bucket = per_word.setdefault(
            w, {"moves": {}, "tickers": set(), "example": (0.0, "")}
        )
        key = (e["ticker"], e["day"])
        bucket["moves"][key] = e["move"]
        bucket["tickers"].add(e["ticker"])
        if e["move"] > bucket["example"][0]:
            bucket["example"] = (e["move"], e["headline"])

    rows = []
    for word, b in per_word.items():
        moves = list(b["moves"].values())
        if len(moves) < 2:
            continue
        avg = sum(moves) / len(moves)
        rows.append(
            {
                "word": word,
                "lift": round(avg / baseline, 2),
                "occurrences": len(moves),
                "avg_move_pct": round(avg * 100, 2),
                "tickers": sorted(b["tickers"])[:4],
                "example_headline": b["example"][1],
            }
        )
    rows.sort(key=lambda r: (r["lift"], r["occurrences"]), reverse=True)
    return rows[:MAX_BUZZWORDS_PER_WINDOW]


def main():
    meta = meta_by_ticker()
    symbols = tickers() + [MARKET_TICKER]

    print(f"Downloading prices for {len(symbols)} symbols…")
    price_df = fetch_all_prices(symbols)
    print(f"  got price history for {len(price_df.columns)} symbols")

    stocks: list[dict] = []
    all_events: list[dict] = []

    print(f"Analyzing {len(UNIVERSE)} stocks (news + NRR)…")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(analyze_one, row["ticker"], meta[row["ticker"]], price_df): row[
                "ticker"
            ]
            for row in UNIVERSE
        }
        for fut in as_completed(futures):
            tkr = futures[fut]
            try:
                entry, events = fut.result()
            except Exception as exc:
                print(f"  {tkr}: failed ({exc})")
                continue
            if entry:
                stocks.append(entry)
                print(f"  {tkr}: NRR={entry['nrr']}  ({entry['n_news_days']} news days)")
            else:
                print(f"  {tkr}: insufficient data (skipped)")
            all_events.extend(events)

    stocks.sort(key=lambda s: s["nrr"], reverse=True)
    sectors = sorted({s["sector"] for s in stocks})

    buzzwords = {name: trending_for_window(all_events, days) for name, days in WINDOWS.items()}

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_benchmark": MARKET_TICKER,
        "period": PERIOD,
        "n_ranked": len(stocks),
        "sectors": sectors,
        "stocks": stocks,
        "buzzwords": buzzwords,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(
        f"\nWrote {OUTPUT_PATH} — {len(stocks)} ranked stocks, "
        f"buzzwords: "
        + ", ".join(f"{k}={len(v)}" for k, v in buzzwords.items())
    )


if __name__ == "__main__":
    main()
