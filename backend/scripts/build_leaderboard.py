"""Precompute the leaderboard snapshot the web app serves.

This is a thin CLI wrapper around ``app.services.leaderboard_build``; the actual
logic lives there so the running server can also rebuild in-process (see the
stale-while-revalidate refresh in ``app.services.leaderboard``).

Usage (from the backend/ directory):

    python3 scripts/build_leaderboard.py

Run it at deploy time (see render.yaml) to seed the snapshot, and optionally on
a schedule (cron, GitHub Action) if you'd rather refresh out-of-band than let
the web service refresh itself on traffic.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when run as a script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.leaderboard_build import build_and_write


def main():
    build_and_write(verbose=True)


if __name__ == "__main__":
    main()
