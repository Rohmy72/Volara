from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from app.services.news_beta import run_news_beta_analysis
from app.services.news_sources import NewsItem


def _make_returns(n_days=120, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_days)
    market = rng.normal(0, 0.008, n_days)
    idio_noise = rng.normal(0, 0.005, n_days)
    ticker = 1.0 * market + idio_noise
    return pd.DataFrame({"ticker": ticker, "market": market}, index=dates)


def _news_item(date: pd.Timestamp, title="Company announces something") -> NewsItem:
    return NewsItem(
        title=f"{title} {date.strftime('%Y-%m-%d')}",
        source="Test Source",
        url="https://example.com",
        published_at=datetime(date.year, date.month, date.day, tzinfo=timezone.utc),
        summary="A test summary.",
    )


def test_news_driven_ticker_yields_high_nrr():
    returns = _make_returns(seed=1)
    news_dates = returns.index[10::5][:15]  # 15 spread-out news days

    # Inject a large idiosyncratic spike specifically on news days.
    returns = returns.copy()
    returns.loc[news_dates, "ticker"] += 0.06

    news_items = [_news_item(d) for d in news_dates]

    result = run_news_beta_analysis(
        returns, news_items, min_news_days=5, min_quiet_days=20, window_days=1
    )

    assert result.status == "ok"
    assert result.nrr is not None
    assert result.nrr > 2.0
    assert result.verdict_label == "News-driven"
    assert result.n_news_days >= 15


def test_insufficient_data_when_too_few_news_days():
    returns = _make_returns(seed=2)
    news_items = [_news_item(returns.index[3])]  # only 1 news day

    result = run_news_beta_analysis(
        returns, news_items, min_news_days=5, min_quiet_days=20
    )

    assert result.status == "insufficient_data"
    assert result.nrr is None
    assert result.verdict_label == "Not enough data"


def test_quiet_ticker_yields_low_nrr():
    returns = _make_returns(seed=3)
    news_dates = returns.index[10::5][:15]
    news_items = [_news_item(d) for d in news_dates]

    # No injected spike on news days -> news days should look like any other day.
    result = run_news_beta_analysis(
        returns, news_items, min_news_days=5, min_quiet_days=20
    )

    assert result.status == "ok"
    assert result.nrr is not None
    assert result.nrr < 2.0
