"""Builds the leaderboard snapshot the web app serves.

Runs the same market-model NRR ("News Beta") analysis used for single-ticker
requests across the whole sector-tagged universe, plus a cross-stock "trending
buzzwords" aggregation bucketed into last-week / last-month / last-year windows.

This module holds the logic so it can be called two ways:

  * from ``scripts/build_leaderboard.py`` (CLI / Render build step), and
  * in-process by ``app.services.leaderboard`` for stale-while-revalidate
    background refreshes, so the board keeps changing as the betas change
    without needing a separate scheduled service.

Each rebuild diffs against the previous snapshot so every stock carries its
rank movement and NRR delta (see ``annotate_deltas``).

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
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from app.data.universe import MARKET_TICKER, UNIVERSE, meta_by_ticker, tickers
from app.services import news_beta, news_sources
from app.services.buzzwords import _ALWAYS_EXCLUDE, _tokenize
from app.services.yahoo_session import session

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "leaderboard.json"

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


def _load_previous() -> dict | None:
    """Read the existing snapshot (if any) to diff the new one against."""
    if not OUTPUT_PATH.exists():
        return None
    try:
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def annotate_deltas(stocks: list[dict], previous: dict | None) -> None:
    """Annotate each stock (in place) with its rank this build, how far it moved
    since the previous snapshot, and how much its News Beta changed.

    ``stocks`` must already be sorted by NRR desc. Movement is expressed so a
    positive ``rank_delta`` means the stock climbed toward the top (more
    news-driven). Stocks absent from the previous snapshot are flagged new.
    """
    prev_by_ticker: dict[str, dict] = {}
    if previous:
        for i, s in enumerate(previous.get("stocks", [])):
            # Prefer the stored rank if present; fall back to list order.
            prev_by_ticker[s["ticker"]] = {
                "rank": s.get("rank", i + 1),
                "nrr": s.get("nrr"),
            }

    for i, s in enumerate(stocks):
        rank = i + 1
        s["rank"] = rank
        prev = prev_by_ticker.get(s["ticker"])
        if prev is None:
            s["is_new"] = True
            s["rank_delta"] = None
            s["nrr_delta"] = None
        else:
            s["is_new"] = False
            # Higher rank number = lower on the board, so improvement is
            # prev_rank - new_rank (positive => climbed).
            s["rank_delta"] = int(prev["rank"] - rank)
            s["nrr_delta"] = (
                round(s["nrr"] - prev["nrr"], 2) if prev.get("nrr") is not None else None
            )


def build_snapshot(verbose: bool = False) -> dict:
    """Run the full universe analysis and return the snapshot dict (does not
    write it). Diffs against the current on-disk snapshot for movement fields."""

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    meta = meta_by_ticker()
    symbols = tickers() + [MARKET_TICKER]

    log(f"Downloading prices for {len(symbols)} symbols…")
    price_df = fetch_all_prices(symbols)
    log(f"  got price history for {len(price_df.columns)} symbols")

    stocks: list[dict] = []
    all_events: list[dict] = []

    log(f"Analyzing {len(UNIVERSE)} stocks (news + NRR)…")
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
                log(f"  {tkr}: failed ({exc})")
                continue
            if entry:
                stocks.append(entry)
                log(f"  {tkr}: NRR={entry['nrr']}  ({entry['n_news_days']} news days)")
            else:
                log(f"  {tkr}: insufficient data (skipped)")
            all_events.extend(events)

    stocks.sort(key=lambda s: s["nrr"], reverse=True)
    annotate_deltas(stocks, _load_previous())

    sectors = sorted({s["sector"] for s in stocks})
    buzzwords = {name: trending_for_window(all_events, days) for name, days in WINDOWS.items()}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_benchmark": MARKET_TICKER,
        "period": PERIOD,
        "n_ranked": len(stocks),
        "sectors": sectors,
        "stocks": stocks,
        "buzzwords": buzzwords,
    }


def write_snapshot(snapshot: dict) -> None:
    """Atomically write the snapshot so a concurrent reader never sees a
    half-written file (the API loader reads it on the request path)."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(OUTPUT_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(snapshot, f, indent=2)
        os.replace(tmp, OUTPUT_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def build_and_write(verbose: bool = False) -> dict:
    snapshot = build_snapshot(verbose=verbose)
    write_snapshot(snapshot)
    if verbose:
        buzz = ", ".join(f"{k}={len(v)}" for k, v in snapshot["buzzwords"].items())
        print(
            f"\nWrote {OUTPUT_PATH} — {snapshot['n_ranked']} ranked stocks, "
            f"buzzwords: {buzz}"
        )
    return snapshot
