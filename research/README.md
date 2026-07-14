# Research: News Reaction Ratio methodology

This folder holds the original research prototype that validated the core
metric the web app is built on, before it became a product.

- **`newsbeta.py`** — the metric itself. Strips market-wide moves out of a
  stock's returns via a market model (`r = alpha + beta * r_market + e`),
  then compares the size of idiosyncratic ("abnormal") moves on news days
  vs quiet days. That ratio is the **News Reaction Ratio (NRR)**:
  - `NRR ~= 1` → news days look like any other day (news-insensitive).
  - `NRR > ~2` → idiosyncratic moves concentrate on news days (news-driven).

  It also includes:
  - `stability_check` — split the sample in half and rank-correlate NRR
    across halves, to check the metric isn't just noise quarter to quarter.
  - `usefulness_check` — correlate NRR against drawdown, Sharpe ratio, and
    post-news-drop recovery time, to check the metric relates to things
    investors actually care about.

- **`run_real_data.py`** — runs the above across a 50-ticker basket using
  free inputs: Yahoo/Stooq prices (via `yfinance`) and Alpha Vantage's
  `NEWS_SENTIMENT` endpoint for ticker-tagged news dates.

## Relationship to the web app

`backend/app/services/news_beta.py` adapts this same market-model + NRR
logic for **single-ticker, on-demand analysis** (the basket/cross-sectional
version here is for validating the metric across many names at once, not
for serving live requests). The web app additionally aligns news to trading
days with a configurable window and layers on buzzword extraction, which
this research code doesn't do.

If you want to re-validate the metric (e.g. after changing the alignment
window or thresholds), this is the place to do it — run it against a fresh
basket and check the stability/usefulness numbers still hold before changing
defaults in `backend/app/core/config.py`.
