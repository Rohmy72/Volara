# Stock News Volatility

Enter a ticker and find out whether its price swings actually track news
coverage — and if so, which headline terms tend to show up on its biggest
move days.

Not investment advice. Correlational signal only.

## How it works

1. **Strip out the market.** We pull daily prices for the ticker and a market
   benchmark (SPY by default) via `yfinance`, and fit a market model
   (`r_ticker = alpha + beta * r_market + e`). The residual `e` is the
   stock's *idiosyncratic* ("abnormal") move — the part not explained by the
   broad market moving.
2. **Pull news for free.** We aggregate yfinance's built-in news feed, Google
   News RSS, and Yahoo Finance RSS for the ticker (no API key needed). If you
   set an `AV_KEY` (Alpha Vantage, free signup), we also blend in its
   `NEWS_SENTIMENT` feed for richer per-article relevance/sentiment scores.
3. **Compute the News Reaction Ratio (NRR).** Each article is aligned to its
   nearest trading day. NRR = average `|abnormal return|` on news days ÷
   average `|abnormal return|` on quiet days.
   - `NRR ~= 1` → news-insensitive: news days move like any other day.
   - `NRR > ~2` → news-driven: idiosyncratic volatility concentrates on news days.
4. **Extract buzzwords.** For each word in the news corpus, compare the
   average move size on days it appeared vs the average across all news
   days. Words with high "lift" are candidate volatility drivers — but this
   is correlational (a word showing up alongside big moves), not a claim of
   causation.

See [`research/README.md`](research/README.md) for the original methodology
validation (stability + usefulness checks across a 50-stock basket) that this
is built on.

## Project layout

```
backend/    FastAPI service — market data, news aggregation, NRR analysis, buzzwords, leaderboards
frontend/   React + Vite UI — ticker input, verdict, price chart, buzzwords, news feed, sidebar leaderboards
research/   Original methodology prototype + basket-level validation script
```

## Leaderboards

The left sidebar shows two leaderboards:

1. **News-driven leaderboard** — stocks ranked by NRR (most vs least news-driven),
   filterable by sector. Click any row to run a full analysis on that ticker.
2. **Trending buzzwords** — headline terms that lined up with the biggest
   idiosyncratic moves across the whole tracked universe, over the last
   week / month / year.

These are served from a **precomputed snapshot** rather than calculated live,
because scoring the whole universe means running the NRR analysis on ~50 stocks
(price history + news for each). Generate/refresh the snapshot with:

```bash
cd backend
python3 scripts/build_leaderboard.py     # writes app/data/leaderboard.json (~1-2 min)
```

The universe (tickers + sectors) lives in [`backend/app/data/universe.py`](backend/app/data/universe.py) —
add names there and re-run the script. Re-run it on a schedule (cron / GitHub
Action) to keep the boards fresh; the API hot-reloads the file when it changes.

> **Data caveat:** free RSS feeds only expose recent articles, so the buzzword
> "year" window is naturally sparse — it can only include as much history as the
> free feeds still carry. The windowing logic is correct; the density is a limit
> of free sources. For the same reason, a stock's NRR in the snapshot can differ
> slightly from a live single-ticker analysis (news is re-fetched at a different
> moment, and the snapshot uses a slightly lower min-news-days threshold).

## Running it locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env    # optional: only needed to set AV_KEY or tweak thresholds
uvicorn app.main:app --reload
```

The API is now at `http://127.0.0.1:8000`. Try:
`http://127.0.0.1:8000/api/analyze/AAPL?period=6mo`

Run tests with:

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` requests to the
backend at `http://127.0.0.1:8000` (see `frontend/vite.config.js`).

## API

`GET /api/analyze/{ticker}?period=1y`

Returns JSON with:
- `verdict` — NRR, label (e.g. "News-driven"), plain-English explanation
- `price_series` — daily close/return/abnormal-return + whether news landed that day
- `buzzwords` — ranked terms with their "lift" over baseline
- `news` — the aggregated, de-duplicated article list

`GET /api/leaderboard` — the precomputed leaderboard snapshot: `stocks` (ranked
by NRR, with `sector`), `sectors` (for filtering), and `buzzwords` bucketed into
`week` / `month` / `year`. Returns 503 if the snapshot hasn't been generated yet.

`GET /api/health` — liveness check.

## Notes & limitations

- **Free sources only by default.** Google News/Yahoo RSS quality varies by
  ticker; small/micro-caps will often hit "Not enough data."
- **Alpha Vantage free tier is rate-limited** (5 req/min, 25 req/day) — it's
  strictly optional and only used if `AV_KEY` is set. The in-memory cache
  (`CACHE_TTL_SECONDS`, default 30 min) helps avoid burning through it.
- **Never commit `.env`.** It's already in `.gitignore`; only `.env.example`
  (with blank values) should ever be committed.
- The in-memory cache is single-process — fine for local/demo use; swap for
  Redis if you deploy this behind multiple workers.
