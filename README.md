# Volara

**News volatility intelligence.** Enter a ticker and find out whether its price
swings actually track news coverage — and if so, which headline terms tend to
show up on its biggest move days.

Not investment advice. Correlational signal only.

## What the website does

The site answers one question: **is this stock news-driven?**

Type a ticker (say `AAPL`), pick a window (3 months to 2 years), and hit
**Analyze**. Volara pulls the stock's price history and every free news article
it can find, strips out the market-wide component of each day's move, and
measures how much bigger the stock's *own* moves are on days it was in the news
versus days it wasn't. That ratio is **News Beta**.

### What you get back

- **The verdict.** A headline card — e.g. *Apple Inc. (AAPL) — Somewhat
  news-sensitive* — with the News Beta score, how many news days and quiet days
  went into it, and what share of the stock's ten biggest moves landed on a news
  day. Read the ratio like this:

  | News Beta | Reading |
  |---|---|
  | ~1.0 | News-insensitive — news days move like any other day |
  | ~1.5 | Somewhat news-sensitive — news contributes but doesn't dominate |
  | >2.0 | News-driven — idiosyncratic volatility concentrates on news days |

- **Price chart, with news days marked.** The daily price line with news days
  flagged, so you can eyeball whether the spikes and the headlines line up.
- **Buzzwords.** Headline terms that showed up disproportionately on the stock's
  biggest idiosyncratic move days, ranked by their "lift" over baseline.
- **The news feed.** The de-duplicated articles the analysis was actually built
  from, so you can check the work.

### The sidebar

Two leaderboards, both served from a precomputed snapshot rather than calculated
live (scoring the universe means running the full analysis on ~50 stocks):

1. **News-driven leaderboard** — the tracked universe ranked from most to least
   news-driven, filterable by sector. Click any row to run a full analysis on it.
2. **Trending buzzwords** — headline terms that lined up with the biggest
   idiosyncratic moves across the *whole* universe over the last week, month, or
   year.

The in-site **"What is News Beta?"** page walks through the full methodology.

## How the number is computed

1. **Strip out the market.** Daily prices for the ticker and a benchmark (SPY by
   default) are fit to a market model (`r_ticker = alpha + beta * r_market + e`).
   The residual `e` is the stock's *idiosyncratic* ("abnormal") move — the part
   the broad market doesn't explain.
2. **Aggregate news, for free.** yfinance's built-in news feed, Google News RSS,
   and Yahoo Finance RSS, de-duplicated. No API key required. If an `AV_KEY`
   (Alpha Vantage, free signup) is set, its `NEWS_SENTIMENT` feed is blended in
   for richer per-article relevance/sentiment scores.
3. **Compute News Beta.** Each article is aligned to its nearest trading day.
   News Beta = average `|abnormal return|` on news days ÷ average
   `|abnormal return|` on quiet days. (It's called the News Reaction Ratio, or
   NRR, in the research code and in API field names.)
4. **Extract buzzwords.** For each word in the news corpus, compare the average
   move size on days it appeared against the average across all news days. Words
   with high lift are candidate volatility drivers — but this is correlational
   (a word appearing alongside big moves), not a causal claim.

See [`research/README.md`](research/README.md) for the original methodology
validation — stability and usefulness checks across a 50-stock basket — that
this is built on.

## Project layout

```
backend/    FastAPI service — market data, news aggregation, News Beta, buzzwords, leaderboards
frontend/   React + Vite UI — ticker input, verdict, price chart, buzzwords, news feed, leaderboards
research/   Original methodology prototype + basket-level validation script
```

## API

The backend is a FastAPI service deployed on Render (see
[`render.yaml`](render.yaml)); the frontend reads it via `VITE_API_BASE_URL`, or
through the Vite dev proxy locally.

`GET /api/analyze/{ticker}?period=1y`
Full analysis for one ticker. `period` accepts any yfinance period string
(`3mo`, `6mo`, `1y`, `2y`). Returns:
- `company_name` — the stock's full name, used for the verdict heading
- `verdict` — News Beta, label, plain-English explanation, news/quiet day counts
- `price_series` — daily close, return, abnormal return, and whether news landed
- `buzzwords` — ranked terms with their lift over baseline
- `news` — the aggregated, de-duplicated article list

`GET /api/leaderboard`
The precomputed snapshot: `stocks` (ranked, with `sector`), `sectors` (for
filtering), and `buzzwords` bucketed into `week` / `month` / `year`. Returns 503
if the snapshot hasn't been generated.

`GET /api/health`
Liveness check — Render's health check path.

Responses are cached in-process (`CACHE_TTL_SECONDS`, default 30 min). The cache
is single-process, which is fine for a single Render instance; swap for Redis if
you scale to multiple workers.

## Fetching data from Yahoo

Yahoo Finance blocks plain HTTP clients coming from datacenter IPs, so a bare
`requests`/`yfinance` call that works on a laptop returns nothing on Render. All
Yahoo traffic therefore goes through one shared session
([`backend/app/services/yahoo_session.py`](backend/app/services/yahoo_session.py))
built with `curl_cffi` and `impersonate="chrome"`, which reproduces Chrome's TLS
fingerprint.

Two things matter if you touch this:

- **`yfinance` must stay recent** (`0.2.66`+). Older versions — including the
  `0.2.43` this project was previously pinned to — cannot accept a `curl_cffi`
  session at all; they expect a `requests.Session` and fail on curl_cffi's
  cookie objects, so *every* download silently returns empty.
- **Don't set a `User-Agent` on that session.** `impersonate="chrome"` already
  supplies one that matches its TLS fingerprint; overriding it with a mismatched
  UA re-flags the request as a bot.

Company names come from Yahoo's lightweight search endpoint rather than
`yf.Ticker(...).info`, which is crumb-protected, heavily rate-limited, and fails
often enough from datacenter IPs that it used to degrade every heading to the
bare ticker. Tickers in the tracked universe fall back to their hard-coded name
if the lookup fails.

## Refreshing the leaderboards

The snapshot is rebuilt at deploy time (it's in the Render build command) and can
be regenerated manually:

```bash
cd backend
python3 scripts/build_leaderboard.py     # writes app/data/leaderboard.json (~1-2 min)
```

The universe lives in
[`backend/app/data/universe.py`](backend/app/data/universe.py) — add tickers
there and re-run. The API hot-reloads the file when it changes. If Yahoo returns
nothing usable, the script now fails loudly rather than overwriting the snapshot
with an empty one, so a bad fetch breaks the build instead of silently shipping
an empty site.

## Notes & limitations

- **Free sources only by default.** Google News/Yahoo RSS quality varies by
  ticker; small and micro-caps will often hit "Not enough data."
- **Free RSS feeds only carry recent articles**, so the buzzword "year" window is
  naturally sparse — it can only include as much history as the feeds still
  expose. The windowing logic is correct; the density is a limit of free sources.
  For the same reason, a stock's News Beta in the snapshot can differ slightly
  from a live single-ticker analysis: news is re-fetched at a different moment,
  and the snapshot uses a slightly lower min-news-days threshold.
- **Alpha Vantage's free tier is rate-limited** (5 req/min, 25 req/day). It's
  strictly optional and only used when `AV_KEY` is set.
- **Never commit `.env`.** It's in `.gitignore`; set `AV_KEY` in the Render
  dashboard, never in `render.yaml`.
- `CORS_ORIGINS` must list the deployed frontend's origin, or the browser will
  block every API call.
