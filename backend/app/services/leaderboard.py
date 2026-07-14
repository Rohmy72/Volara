"""Serves the precomputed leaderboard snapshot written by
scripts/build_leaderboard.py. Reads the JSON from disk and caches it in memory,
reloading automatically when the file changes (so a rebuild is picked up
without restarting the server).
"""
from __future__ import annotations

import json
from pathlib import Path

_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "leaderboard.json"

_cache: dict | None = None
_cache_mtime: float | None = None


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

    return _cache
