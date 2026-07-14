from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from scipy import stats


class _stats:
    @staticmethod
    def linregress(x, y):
        x = np.asarray(x)
        y = np.asarray(y)
        mask = ~np.isnan(x) & ~np.isnan(y)
        x = x[mask]
        y = y[mask]
        if len(x) < 2:
            return np.nan, np.nan, np.nan, np.nan, np.nan
        x_mean = x.mean()
        y_mean = y.mean()
        dx = x - x_mean
        dy = y - y_mean
        sxx = np.dot(dx, dx)
        sxy = np.dot(dx, dy)
        beta = sxy / sxx if sxx != 0 else np.nan
        alpha = y_mean - beta * x_mean
        return beta, alpha, np.nan, np.nan, np.nan

    @staticmethod
    def spearmanr(a, b):
        a = np.asarray(a)
        b = np.asarray(b)
        mask = ~np.isnan(a) & ~np.isnan(b)
        a = a[mask]
        b = b[mask]
        if len(a) < 2:
            return np.nan, np.nan
        a_rank = pd.Series(a).rank().to_numpy()
        b_rank = pd.Series(b).rank().to_numpy()
        a_dev = a_rank - a_rank.mean()
        b_dev = b_rank - b_rank.mean()
        denom = np.sqrt(np.dot(a_dev, a_dev) * np.dot(b_dev, b_dev))
        rho = np.dot(a_dev, b_dev) / denom if denom != 0 else np.nan
        return rho, np.nan


stats = _stats()


# ---------------------------------------------------------------------------
# Step 1: strip out the market so we measure IDIOSYNCRATIC moves only.
# A stock dropping because the whole market dropped is not "news reactivity".
# We fit the market model  r_i = alpha + beta*r_mkt + e   and keep e (abnormal).
# ---------------------------------------------------------------------------
def abnormal_returns(prices: pd.DataFrame, market_col: str) -> pd.DataFrame:
    rets = prices.pct_change().dropna(how="all")
    mkt = rets[market_col]
    out = {}
    for tkr in rets.columns:
        if tkr == market_col:
            continue
        y = rets[tkr]
        df = pd.concat([y, mkt], axis=1).dropna()
        if len(df) < 60:
            continue
        beta, alpha, *_ = stats.linregress(df[market_col], df[tkr])
        out[tkr] = df[tkr] - (alpha + beta * df[market_col]) # type: ignore
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Step 2: the metric itself — News Reaction Ratio (NRR).
#   NRR = mean(|abnormal return| on NEWS days) / mean(|abnormal return| on quiet days)
#
#   NRR ~= 1   -> news days look like any other day. News-INSENSITIVE.
#   NRR  > 2   -> idiosyncratic moves concentrate hard on news. News-DRIVEN ("hype").
#
# We only trust a ticker with enough news days to estimate the numerator.
# ---------------------------------------------------------------------------
def compute_news_beta(
    abn: pd.DataFrame,
    news_dates: dict[str, set],
    min_news_days: int = 8,
) -> pd.DataFrame:
    rows = []
    for tkr in abn.columns:
        s = abn[tkr].dropna()
        nd = news_dates.get(tkr, set())
        is_news = s.index.isin(nd)
        n_news = int(is_news.sum())
        n_quiet = int((~is_news).sum())
        if n_news < min_news_days or n_quiet < 30:
            continue
        news_mag = s[is_news].abs().mean()
        quiet_mag = s[~is_news].abs().mean()
        nrr = news_mag / quiet_mag if quiet_mag > 0 else np.nan
        rows.append(
            dict(ticker=tkr, news_beta=nrr, n_news_days=n_news,
                 news_day_move=news_mag, quiet_day_move=quiet_mag)
        )
    return (pd.DataFrame(rows)
            .set_index("ticker")
            .sort_values("news_beta", ascending=False))


# ---------------------------------------------------------------------------
# Q2: STABILITY. If a stock's news-beta is random noise quarter to quarter,
# the product's core claim ("this name is news-insensitive") is a lie.
# We split the sample in half, rank stocks by news-beta in each half,
# and measure Spearman rank correlation. High corr = the ordering persists.
# ---------------------------------------------------------------------------
def stability_check(abn: pd.DataFrame, news_dates: dict[str, set],
                    min_news_days: int = 5) -> dict:
    mid = len(abn) // 2
    first = compute_news_beta(abn.iloc[:mid], news_dates, min_news_days)
    second = compute_news_beta(abn.iloc[mid:], news_dates, min_news_days)
    common = first.index.intersection(second.index)
    if len(common) < 5:
        return dict(rank_corr=np.nan, n=len(common))
    rho, p = stats.spearmanr(first.loc[common, "news_beta"],
                             second.loc[common, "news_beta"])
    return dict(rank_corr=rho, p_value=p, n=len(common))


# ---------------------------------------------------------------------------
# Q3: USEFULNESS. A metric nobody can act on is trivia. We test whether
# news-beta relates to things investors actually feel:
#   - max drawdown (does low news-beta = smoother ride?)
#   - Sharpe-ish ratio (risk-adjusted return)
#   - recovery: after a big news-day drop, how fast does it revert?
# ---------------------------------------------------------------------------
def _max_drawdown(price: pd.Series) -> float:
    roll_max = price.cummax()
    return (price / roll_max - 1).min()


def _recovery_days(abn: pd.Series, news_dates: set, drop_thresh=-0.03,
                   horizon=15) -> float:
    """Avg trading days to claw back a >3% news-day abnormal drop (capped at horizon)."""
    idx = abn.index
    news_mask = idx.isin(news_dates)
    drops = abn[(abn < drop_thresh) & news_mask]
    recs = []
    for d in drops.index:
        loc = idx.get_loc(d)
        cum = 0.0
        rec = horizon
        for k in range(1, horizon + 1):
            if loc + k >= len(idx): # type: ignore
                break
            cum += abn.iloc[loc + k] # type: ignore
            if cum >= -drops[d]:  # recovered the abnormal drop
                rec = k
                break
        recs.append(rec)
    return float(np.mean(recs)) if recs else np.nan


def usefulness_check(prices, abn, news_beta_df, news_dates) -> pd.DataFrame:
    rets = prices.pct_change()
    rows = []
    for tkr in news_beta_df.index:
        if tkr not in prices.columns:
            continue
        p = prices[tkr].dropna()
        r = rets[tkr].dropna()
        sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
        rows.append(dict(
            ticker=tkr,
            news_beta=news_beta_df.loc[tkr, "news_beta"],
            max_drawdown=_max_drawdown(p),
            sharpe=sharpe,
            recovery_days=_recovery_days(abn[tkr].dropna(),
                                         news_dates.get(tkr, set())),
        ))
    df = pd.DataFrame(rows).set_index("ticker")

    corrs = {}
    for col in ["max_drawdown", "sharpe", "recovery_days"]:
        sub = df[["news_beta", col]].dropna()
        if len(sub) >= 6:
            rho, p = stats.spearmanr(sub["news_beta"], sub[col])
            corrs[col] = (rho, p, len(sub))
    return df, corrs # pyright: ignore[reportReturnType]
