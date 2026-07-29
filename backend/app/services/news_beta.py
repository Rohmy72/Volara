"""Market-model based 'News Reaction Ratio' (NRR) analysis.

This adapts the methodology validated in research/newsbeta.py to a single
ticker, live-analysis setting:

  1. Fit a market model  r_ticker = alpha + beta * r_market + e  (vs SPY by
     default) so we measure IDIOSYNCRATIC (abnormal) moves only. A stock
     dropping because the whole market dropped is not "news reactivity."
  2. Align news articles to the nearest trading day.
  3. NRR = mean(|abnormal return| on news days) / mean(|abnormal return| on
     quiet days).
       NRR ~= 1   -> news days look like any other day (news-insensitive).
       NRR  > ~2  -> idiosyncratic moves concentrate on news days (news-driven).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.services.news_sources import NewsItem

NEWS_DRIVEN_THRESHOLD = 2.0
SOMEWHAT_SENSITIVE_THRESHOLD = 1.2


# A news day is only counted as directional if its abnormal move clears this
# threshold (in return terms); flat days near zero shouldn't tilt the skew.
DIRECTION_MIN_ABS_MOVE = 0.001  # 0.1%
# Up-share cutoffs for the directional label.
UPSIDE_SHARE = 0.60
DOWNSIDE_SHARE = 0.40


@dataclass
class NewsBetaResult:
    status: str  # "ok" | "insufficient_data"
    nrr: float | None
    n_news_days: int
    n_quiet_days: int
    news_day_avg_abs_move: float | None
    quiet_day_avg_abs_move: float | None
    top_moves_explained_pct: float | None
    verdict_label: str
    verdict_explanation: str
    abnormal_returns: pd.Series
    # Directional bias: which way news-day moves lean, from the *signed*
    # abnormal returns (News Beta itself only looks at magnitude).
    direction_label: str | None = None
    direction_explanation: str | None = None
    news_day_up_share: float | None = None
    n_news_up_days: int = 0
    n_news_down_days: int = 0
    news_day_avg_signed_pct: float | None = None
    avg_up_move_pct: float | None = None
    avg_down_move_pct: float | None = None
    news_day_map: dict[pd.Timestamp, list[NewsItem]] = field(default_factory=dict)


def fit_market_model(returns: pd.DataFrame) -> tuple[float, float]:
    """OLS fit of ticker returns on market returns. Returns (alpha, beta)."""
    df = returns[["ticker", "market"]].dropna()
    x = df["market"].to_numpy()
    y = df["ticker"].to_numpy()
    x_mean, y_mean = x.mean(), y.mean()
    dx, dy = x - x_mean, y - y_mean
    var_x = np.dot(dx, dx)
    beta = float(np.dot(dx, dy) / var_x) if var_x != 0 else 0.0
    alpha = float(y_mean - beta * x_mean)
    return alpha, beta


def compute_abnormal_returns(returns: pd.DataFrame) -> pd.Series:
    alpha, beta = fit_market_model(returns)
    df = returns[["ticker", "market"]].dropna()
    abnormal = df["ticker"] - (alpha + beta * df["market"])
    abnormal.name = "abnormal_return"
    return abnormal


def align_news_to_trading_days(
    news_items: list[NewsItem],
    trading_days: pd.DatetimeIndex,
    window_days: int = 1,
) -> dict[pd.Timestamp, list[NewsItem]]:
    """Map each news item to its nearest trading day within `window_days`."""
    trading_days = trading_days.sort_values()
    mapping: dict[pd.Timestamp, list[NewsItem]] = {}

    for item in news_items:
        pub_date = pd.Timestamp(item.published_at).tz_localize(None).normalize()
        window = trading_days[
            (trading_days >= pub_date - pd.Timedelta(days=window_days))
            & (trading_days <= pub_date + pd.Timedelta(days=window_days))
        ]
        if len(window) == 0:
            continue
        nearest = min(window, key=lambda d: abs((d - pub_date).days))
        mapping.setdefault(nearest, []).append(item)

    return mapping


def _classify_verdict(nrr: float | None, status: str, n_news_days: int) -> tuple[str, str]:
    if status == "insufficient_data" or nrr is None:
        return (
            "Not enough data",
            f"Only {n_news_days} aligned news day(s) found in this window — "
            "too few to draw a reliable conclusion. Try a longer period or a "
            "more widely covered ticker.",
        )
    if nrr >= NEWS_DRIVEN_THRESHOLD:
        return (
            "News-driven",
            f"Idiosyncratic price moves on news days are {nrr:.1f}x larger than on "
            "quiet days — this stock's volatility looks strongly tied to news flow.",
        )
    if nrr >= SOMEWHAT_SENSITIVE_THRESHOLD:
        return (
            "Somewhat news-sensitive",
            f"News days show moderately larger idiosyncratic moves ({nrr:.1f}x quiet "
            "days) — news is a contributing factor but not the dominant driver.",
        )
    return (
        "Not particularly news-driven",
        f"News days move about the same as (or less than) quiet days ({nrr:.1f}x) — "
        "this stock's volatility doesn't appear concentrated around news events.",
    )


def top_moves_explained_pct(
    abnormal: pd.Series, news_days: set[pd.Timestamp], top_n: int = 10
) -> float | None:
    if abnormal.empty:
        return None
    top_n = min(top_n, len(abnormal))
    top_days = abnormal.abs().sort_values(ascending=False).head(top_n).index
    hits = sum(1 for d in top_days if d in news_days)
    return round(100 * hits / top_n, 1)


def compute_directional_bias(
    abnormal: pd.Series, news_days: set[pd.Timestamp]
) -> dict:
    """From the *signed* abnormal returns on news days, work out which way the
    stock's news reactions lean. News Beta measures how big news-day moves are;
    this measures whether they're gains or losses.

    Returns a dict of directional fields (label/explanation + the counts and
    averages behind them). All values are None/0 when there aren't enough
    directional news days to say anything.
    """
    empty = {
        "direction_label": None,
        "direction_explanation": None,
        "news_day_up_share": None,
        "n_news_up_days": 0,
        "n_news_down_days": 0,
        "news_day_avg_signed_pct": None,
        "avg_up_move_pct": None,
        "avg_down_move_pct": None,
    }
    if abnormal.empty or not news_days:
        return empty

    news_abn = abnormal[abnormal.index.isin(news_days)].dropna()
    directional = news_abn[news_abn.abs() >= DIRECTION_MIN_ABS_MOVE]
    ups = directional[directional > 0]
    downs = directional[directional < 0]
    n_up, n_down = int(len(ups)), int(len(downs))
    total = n_up + n_down
    if total == 0:
        return empty

    up_share = n_up / total
    avg_signed_pct = round(float(news_abn.mean()) * 100, 2)
    avg_up_pct = round(float(ups.mean()) * 100, 2) if n_up else None
    avg_down_pct = round(float(downs.mean()) * 100, 2) if n_down else None

    if up_share >= UPSIDE_SHARE:
        label = "Upside-skewed"
        lean = f"rose on {n_up} of {total} news days"
    elif up_share <= DOWNSIDE_SHARE:
        label = "Downside-skewed"
        lean = f"fell on {n_down} of {total} news days"
    else:
        label = "Two-sided"
        lean = f"split roughly evenly ({n_up} up, {n_down} down)"

    explanation = (
        f"After stripping out the market, this stock {lean} — the average "
        f"news-day move was {avg_signed_pct:+.2f}%."
    )
    # Note any asymmetry in reaction size (e.g. bad news hits harder).
    if avg_up_pct is not None and avg_down_pct is not None:
        up_mag, down_mag = avg_up_pct, abs(avg_down_pct)
        if down_mag >= up_mag * 1.5:
            explanation += (
                f" Down reactions are larger on average ({avg_down_pct:.2f}%) "
                f"than up ones (+{up_mag:.2f}%)."
            )
        elif up_mag >= down_mag * 1.5:
            explanation += (
                f" Up reactions are larger on average (+{up_mag:.2f}%) than "
                f"down ones ({avg_down_pct:.2f}%)."
            )

    return {
        "direction_label": label,
        "direction_explanation": explanation,
        "news_day_up_share": round(up_share, 3),
        "n_news_up_days": n_up,
        "n_news_down_days": n_down,
        "news_day_avg_signed_pct": avg_signed_pct,
        "avg_up_move_pct": avg_up_pct,
        "avg_down_move_pct": avg_down_pct,
    }


def run_news_beta_analysis(
    returns: pd.DataFrame,
    news_items: list[NewsItem],
    min_news_days: int = 5,
    min_quiet_days: int = 20,
    window_days: int = 1,
) -> NewsBetaResult:
    abnormal = compute_abnormal_returns(returns)
    news_day_map = align_news_to_trading_days(news_items, abnormal.index, window_days)
    news_days = set(news_day_map.keys())

    is_news_day = abnormal.index.to_series().isin(news_days)
    n_news_days = int(is_news_day.sum())
    n_quiet_days = int((~is_news_day).sum())

    if n_news_days < min_news_days or n_quiet_days < min_quiet_days:
        label, explanation = _classify_verdict(None, "insufficient_data", n_news_days)
        return NewsBetaResult(
            status="insufficient_data",
            nrr=None,
            n_news_days=n_news_days,
            n_quiet_days=n_quiet_days,
            news_day_avg_abs_move=None,
            quiet_day_avg_abs_move=None,
            top_moves_explained_pct=top_moves_explained_pct(abnormal, news_days),
            verdict_label=label,
            verdict_explanation=explanation,
            abnormal_returns=abnormal,
            news_day_map=news_day_map,
        )

    news_mag = float(abnormal[is_news_day].abs().mean())
    quiet_mag = float(abnormal[~is_news_day].abs().mean())
    nrr = news_mag / quiet_mag if quiet_mag > 0 else None

    label, explanation = _classify_verdict(nrr, "ok", n_news_days)

    return NewsBetaResult(
        status="ok",
        nrr=round(nrr, 2) if nrr is not None else None,
        n_news_days=n_news_days,
        n_quiet_days=n_quiet_days,
        news_day_avg_abs_move=round(news_mag, 4),
        quiet_day_avg_abs_move=round(quiet_mag, 4),
        top_moves_explained_pct=top_moves_explained_pct(abnormal, news_days),
        verdict_label=label,
        verdict_explanation=explanation,
        abnormal_returns=abnormal,
        news_day_map=news_day_map,
        **compute_directional_bias(abnormal, news_days),
    )
