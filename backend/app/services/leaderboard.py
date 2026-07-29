"""Serves the leaderboard snapshot written by leaderboard_build.

The snapshot is read from disk and cached in memory, reloading automatically
when the file changes (so a rebuild is picked up without restarting the server).

To keep the board changing as the betas change, this module also does
stale-while-revalidate: when a request finds the snapshot older than
``settings.leaderboard_max_age_hours``, it serves the current (stale) snapshot
immediately and kicks off an in-process rebuild in a background thread. The
rebuild writes a fresh snapshot atomically, which the next request picks up.
This is driven by traffic, so it works on a single free web instance without a
separate scheduled service.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "leaderboard.json"

_cache: dict | None = None
_cache_mtime: float | None = None

_refresh_lock = threading.Lock()
_refreshing = False


class LeaderboardUnavailable(Exception):
    pass


def load_snapshot() -> dict:
    global _cache, _cache_mtime

    if not _SNAPSHOT_PATH.exists():
        raise LeaderboardUnavailable(
            "Leaderboard snapshot not found. Generate it by running "
            "`python3 scripts/build_leaderboard.py` from the backend directory."
        )

    mtime = _SNAPSHOT_PATH.stat().st_mtime
    if _cache is None or mtime != _cache_mtime:
        with open(_SNAPSHOT_PATH) as f:
            _cache = json.load(f)
        _cache_mtime = mtime

    return _cache  # type: ignore


def is_refreshing() -> bool:
    return _refreshing


def snapshot_age_hours(snapshot: dict) -> float | None:
    """Age of the snapshot in hours, or None if it has no usable timestamp."""
    ts = snapshot.get("generated_at")
    if not ts:
        return None
    try:
        generated = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - generated).total_seconds() / 3600.0


def _run_refresh() -> None:
    global _refreshing
    try:
        # Imported lazily so importing this module (and the API) doesn't pull in
        # yfinance/pandas until a refresh actually runs.
        from app.services.leaderboard_build import build_and_write

        build_and_write(verbose=False)
    except Exception:
        # A failed rebuild must never take the endpoint down — we simply keep
        # serving the existing snapshot and try again on the next stale request.
        pass
    finally:
        with _refresh_lock:
            _refreshing = False


def maybe_refresh(snapshot: dict) -> None:
    """If auto-refresh is enabled and the snapshot is stale, trigger a single
    background rebuild. No-op if a rebuild is already in flight."""
    global _refreshing

    if not settings.leaderboard_auto_refresh:
        return

    age = snapshot_age_hours(snapshot)
    if age is not None and age < settings.leaderboard_max_age_hours:
        return

    with _refresh_lock:
        if _refreshing:
            return
        _refreshing = True

    thread = threading.Thread(
        target=_run_refresh, name="leaderboard-refresh", daemon=True
    )
    thread.start()
