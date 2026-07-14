"""
run_real_data.py — Run the SAME analysis on REAL stocks.

Run this on your own machine (this sandbox can't reach these hosts).
Two free inputs, no paid news license required for the pilot:

  PRICES  — Stooq.  Free CSV, no key:  https://stooq.com/q/d/l/?s=aapl.us&i=d
  NEWS    — Alpha Vantage NEWS_SENTIMENT.  Free key (5 req/min, 25/day):
            https://www.alphavantage.co/support/#api-key
            Endpoint returns articles already TAGGED with tickers + timestamps,
            so you get real news-event dates without a Bloomberg license.
            (Free tier history is limited; for a longer window use GDELT's
            free DOC 2.0 API, or Tiingo/Finnhub free news tiers.)

Steps:
  pip install requests pandas numpy scipy matplotlib
  export AV_KEY=your_alpha_vantage_key
  python run_real_data.py
"""

import io, os, time, requests
import pandas as pd
from newsbeta import (abnormal_returns, compute_news_beta,
                      stability_check, usefulness_check)

# A starter basket of 50 — deliberately spans "steady" and "hype" names so the
# spread is visible. Swap in whatever universe you actually care about.
TICKERS = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AMD","NFLX","CRM",
    "JPM","BAC","WFC","GS","V","MA","BRK-B","KO","PEP","PG",
    "JNJ","PFE","MRK","UNH","ABBV","XOM","CVX","COP","WMT","HD",
    "COST","MCD","DIS","VZ","T","INTC","CSCO","ORCL","IBM","QCOM",
    "PLTR","COIN","RIVN","LCID","MSTR","GME","AMC","SOFI","HOOD","RBLX",
]
MARKET = "SPY"


def stooq_prices(tickers, start="2022-01-01"):
    """Daily closes from Yahoo via yfinance (reliable; no key)."""
    import yfinance as yf
    syms = tickers + [MARKET]
    data = yf.download(syms, start=start, auto_adjust=True,
                       progress=False)["Close"]
    if isinstance(data, pd.Series):          # single ticker edge case
        data = data.to_frame()
    got = [c for c in data.columns if data[c].notna().sum() > 100]
    missing = [t for t in syms if t not in got]
    if missing:
        print("no price data for:", missing)
    return data[got].sort_index().ffill().dropna(how="all")


def av_news_dates(tickers, key):
    """Real news-event dates per ticker from Alpha Vantage NEWS_SENTIMENT."""
    out = {}
    for t in tickers:
        url = ("https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
               f"&tickers={t}&limit=1000&apikey={key}")
        try:
            js = requests.get(url, timeout=25).json()
            dates = set()
            for art in js.get("feed", []):
                # keep only articles where THIS ticker is materially relevant
                for ts in art.get("ticker_sentiment", []):
                    if ts["ticker"] == t and float(ts["relevance_score"]) >= 0.5:
                        dates.add(pd.to_datetime(art["time_published"][:8]).normalize())
            out[t] = dates
            print(f"{t}: {len(dates)} news days")
            time.sleep(13)   # free tier = 5 req/min
        except Exception as e:
            print("news fail", t, e); out[t] = set()
    return out


if __name__ == "__main__":
    key = os.environ.get("AV_KEY")
    assert key, "set AV_KEY env var (free Alpha Vantage key)"

    prices = stooq_prices(TICKERS)
    news = av_news_dates([t for t in TICKERS if t in prices.columns], key)

    abn = abnormal_returns(prices, market_col=MARKET)
    nb = compute_news_beta(abn, news)
    stab = stability_check(abn, news)
    use_df, corrs = usefulness_check(prices, abn, nb, news)

    print("\n===== MOST news-driven =====");  print(nb.head(8).round(2))
    print("\n===== LEAST news-driven ====="); print(nb.tail(8).round(2))
    print(f"\nStability (half vs half): rho={stab['rank_corr']:.2f}  n={stab['n']}")
    print("\nUsefulness correlations:")
    for k, (rho, p, n) in corrs.items():
        print(f"  news_beta vs {k:<14} rho={rho:+.2f}  p={p:.3f}  n={n}")

    nb.to_csv("news_beta_results.csv")
    print("\nSaved -> news_beta_results.csv")
