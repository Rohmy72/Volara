from datetime import datetime, timedelta, timezone

from app.services import leaderboard
from app.services.leaderboard_build import annotate_deltas


def test_annotate_deltas_marks_movement_and_new():
    previous = {
        "stocks": [
            {"ticker": "AAPL", "nrr": 2.5, "rank": 1},
            {"ticker": "TSLA", "nrr": 2.0, "rank": 2},
            {"ticker": "MSFT", "nrr": 1.5, "rank": 3},
        ]
    }
    # New ranking (already sorted by nrr desc): TSLA climbs, NVDA is new,
    # AAPL falls, MSFT falls.
    stocks = [
        {"ticker": "TSLA", "nrr": 2.6},
        {"ticker": "NVDA", "nrr": 2.1},
        {"ticker": "AAPL", "nrr": 2.0},
        {"ticker": "MSFT", "nrr": 1.4},
    ]
    annotate_deltas(stocks, previous)
    by_ticker = {s["ticker"]: s for s in stocks}

    assert by_ticker["TSLA"]["rank"] == 1
    assert by_ticker["TSLA"]["rank_delta"] == 1  # 2 -> 1, climbed
    assert by_ticker["TSLA"]["nrr_delta"] == 0.6

    assert by_ticker["NVDA"]["is_new"] is True
    assert by_ticker["NVDA"]["rank_delta"] is None

    assert by_ticker["AAPL"]["rank_delta"] == -2  # 1 -> 3, fell
    assert by_ticker["AAPL"]["nrr_delta"] == -0.5
    assert by_ticker["MSFT"]["rank_delta"] == -1


def test_annotate_deltas_no_previous_snapshot():
    stocks = [{"ticker": "AAPL", "nrr": 2.5}]
    annotate_deltas(stocks, None)
    assert stocks[0]["rank"] == 1
    assert stocks[0]["is_new"] is True
    assert stocks[0]["rank_delta"] is None


def test_snapshot_age_hours():
    old = {
        "generated_at": (
            datetime.now(timezone.utc) - timedelta(hours=30)
        ).isoformat()
    }
    age = leaderboard.snapshot_age_hours(old)
    assert age is not None and 29.5 < age < 30.5

    assert leaderboard.snapshot_age_hours({}) is None


def test_maybe_refresh_skips_fresh_snapshot(monkeypatch):
    calls = []
    monkeypatch.setattr(
        leaderboard.settings, "leaderboard_auto_refresh", True, raising=False
    )
    monkeypatch.setattr(
        leaderboard.settings, "leaderboard_max_age_hours", 12, raising=False
    )
    monkeypatch.setattr(
        leaderboard.threading, "Thread", lambda *a, **k: calls.append((a, k))
    )

    fresh = {"generated_at": datetime.now(timezone.utc).isoformat()}
    leaderboard.maybe_refresh(fresh)
    assert calls == []  # fresh snapshot => no rebuild thread spawned
