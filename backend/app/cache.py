"""Tiny in-memory TTL cache so repeated requests for the same ticker don't
re-hit yfinance / news RSS feeds (and don't burn a rate-limited API key).

This is intentionally simple (single-process, no persistence). Swap for
Redis if you deploy this beyond a single instance.
"""
from __future__ import annotations

import time
from threading import Lock

_store: dict[str, tuple[float, object]] = {}
_lock = Lock()


def get(key: str):
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del _store[key]
            return None
        return value


def set(key: str, value: object, ttl_seconds: int) -> None:
    with _lock:
        _store[key] = (time.time() + ttl_seconds, value)
