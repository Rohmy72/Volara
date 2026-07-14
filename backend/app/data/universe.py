"""The stock universe scored for the leaderboards.

Each entry is (ticker, display name, sector). Names/sectors are hard-coded so
the build script doesn't have to make ~50 slow, rate-limited yfinance `.info`
calls just to label rows. Extend this list to score more names — the build
script and API pick everything up automatically.
"""

UNIVERSE: list[dict[str, str]] = [
    # --- Technology ---------------------------------------------------------
    {"ticker": "AAPL", "name": "Apple", "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Technology"},
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Technology"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology"},
    {"ticker": "INTC", "name": "Intel", "sector": "Technology"},
    {"ticker": "CSCO", "name": "Cisco", "sector": "Technology"},
    {"ticker": "ORCL", "name": "Oracle", "sector": "Technology"},
    {"ticker": "IBM", "name": "IBM", "sector": "Technology"},
    {"ticker": "QCOM", "name": "Qualcomm", "sector": "Technology"},
    {"ticker": "CRM", "name": "Salesforce", "sector": "Technology"},
    # --- Communication ------------------------------------------------------
    {"ticker": "GOOGL", "name": "Alphabet", "sector": "Communication"},
    {"ticker": "META", "name": "Meta Platforms", "sector": "Communication"},
    {"ticker": "NFLX", "name": "Netflix", "sector": "Communication"},
    {"ticker": "DIS", "name": "Disney", "sector": "Communication"},
    {"ticker": "VZ", "name": "Verizon", "sector": "Communication"},
    {"ticker": "T", "name": "AT&T", "sector": "Communication"},
    # --- Consumer Discretionary --------------------------------------------
    {"ticker": "AMZN", "name": "Amazon", "sector": "Consumer Discretionary"},
    {"ticker": "TSLA", "name": "Tesla", "sector": "Consumer Discretionary"},
    {"ticker": "HD", "name": "Home Depot", "sector": "Consumer Discretionary"},
    {"ticker": "MCD", "name": "McDonald's", "sector": "Consumer Discretionary"},
    {"ticker": "NKE", "name": "Nike", "sector": "Consumer Discretionary"},
    {"ticker": "SBUX", "name": "Starbucks", "sector": "Consumer Discretionary"},
    # --- Consumer Staples ---------------------------------------------------
    {"ticker": "KO", "name": "Coca-Cola", "sector": "Consumer Staples"},
    {"ticker": "PEP", "name": "PepsiCo", "sector": "Consumer Staples"},
    {"ticker": "PG", "name": "Procter & Gamble", "sector": "Consumer Staples"},
    {"ticker": "WMT", "name": "Walmart", "sector": "Consumer Staples"},
    {"ticker": "COST", "name": "Costco", "sector": "Consumer Staples"},
    # --- Financials ---------------------------------------------------------
    {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financials"},
    {"ticker": "BAC", "name": "Bank of America", "sector": "Financials"},
    {"ticker": "WFC", "name": "Wells Fargo", "sector": "Financials"},
    {"ticker": "GS", "name": "Goldman Sachs", "sector": "Financials"},
    {"ticker": "V", "name": "Visa", "sector": "Financials"},
    {"ticker": "MA", "name": "Mastercard", "sector": "Financials"},
    # --- Healthcare ---------------------------------------------------------
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "PFE", "name": "Pfizer", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "Merck", "sector": "Healthcare"},
    {"ticker": "UNH", "name": "UnitedHealth", "sector": "Healthcare"},
    {"ticker": "ABBV", "name": "AbbVie", "sector": "Healthcare"},
    # --- Energy -------------------------------------------------------------
    {"ticker": "XOM", "name": "ExxonMobil", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "sector": "Energy"},
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy"},
    # --- Speculative / High-beta -------------------------------------------
    {"ticker": "PLTR", "name": "Palantir", "sector": "Speculative"},
    {"ticker": "COIN", "name": "Coinbase", "sector": "Speculative"},
    {"ticker": "MSTR", "name": "MicroStrategy", "sector": "Speculative"},
    {"ticker": "RIVN", "name": "Rivian", "sector": "Speculative"},
    {"ticker": "LCID", "name": "Lucid", "sector": "Speculative"},
    {"ticker": "GME", "name": "GameStop", "sector": "Speculative"},
    {"ticker": "AMC", "name": "AMC Entertainment", "sector": "Speculative"},
    {"ticker": "SOFI", "name": "SoFi", "sector": "Speculative"},
    {"ticker": "HOOD", "name": "Robinhood", "sector": "Speculative"},
    {"ticker": "RBLX", "name": "Roblox", "sector": "Speculative"},
]

MARKET_TICKER = "SPY"


def tickers() -> list[str]:
    return [row["ticker"] for row in UNIVERSE]


def meta_by_ticker() -> dict[str, dict[str, str]]:
    return {row["ticker"]: row for row in UNIVERSE}
