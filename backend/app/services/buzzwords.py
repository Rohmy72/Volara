"""Finds words in news headlines/summaries that coincide with bigger price moves.

Method: for each word, look at every trading day it appeared in the news on,
and compare the average |abnormal return| of those days against the average
across all news days. A word with a "lift" > 1 tends to show up on the more
volatile news days — i.e. a candidate volatility "buzzword". This is a
correlational signal, not a causal one, and is presented that way in the UI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from app.services.news_sources import NewsItem

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")

_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "could", "did", "do", "does",
    "doing", "down", "during", "each", "few", "for", "from", "further", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "s", "same", "she", "should", "so", "some", "such", "t", "than",
    "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself",
    "yourselves", "vs", "via", "amid", "amid", "into", "onto",
}

_FINANCE_FILLER = {
    "stock", "stocks", "share", "shares", "inc", "corp", "corporation", "ltd",
    "nasdaq", "nyse", "says", "say", "said", "market", "markets", "price",
    "prices", "today", "week", "weekly", "year", "yearly", "according", "report",
    "reports", "reported", "news", "update", "updates", "new", "co", "company",
    "companys", "quarter", "quarterly", "trading", "trade", "trades", "investor",
    "investors", "investing", "here", "why", "what", "top", "best",
    # Generic price-recap boilerplate ("Stock Moved X% Today: Drivers Behind
    # It"). These describe the move itself rather than a cause, so they'd
    # trivially correlate with big-move days and drown out real signal.
    "moved", "moves", "move", "movement", "movements", "driven", "driving",
    "drivers", "driver", "behind", "session", "sessions", "close", "closed",
    "closing", "open", "opened", "opening", "point", "points", "percent",
    "percentage", "know", "facts", "fact", "significant", "significantly",
    "broader", "gain", "gains", "gained", "gaining", "fell", "falls",
    "falling", "fallen", "rose", "rises", "rising", "risen", "surge",
    "surged", "surging", "plunge", "plunged", "plunging", "jump", "jumped",
    "jumping", "climb", "climbed", "climbing", "slide", "slid", "sliding",
    "tumble", "tumbled", "rally", "rallied", "rallying", "day", "days",
}

_ALWAYS_EXCLUDE = _STOPWORDS | _FINANCE_FILLER


@dataclass
class Buzzword:
    word: str
    lift: float
    occurrences: int
    avg_move_pct: float
    example_headline: str


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2}


def extract_buzzwords(
    news_day_map: dict[pd.Timestamp, list[NewsItem]],
    abnormal_returns: pd.Series,
    ticker: str,
    company_name: str | None = None,
    min_occurrences: int = 2,
    top_n: int = 15,
) -> list[Buzzword]:
    exclude = set(_ALWAYS_EXCLUDE)
    exclude.add(ticker.lower())
    if company_name:
        exclude.update(_tokenize(company_name))

    day_moves: dict[str, list[float]] = {}
    day_examples: dict[str, tuple[float, str]] = {}
    all_moves: list[float] = []

    for day, items in news_day_map.items():
        if day not in abnormal_returns.index:
            continue
        move = abs(float(abnormal_returns.loc[day]))
        if pd.isna(move):
            continue
        all_moves.append(move)

        day_tokens: set[str] = set()
        headline_for_token: dict[str, str] = {}
        for item in items:
            tokens = _tokenize(item.title) | _tokenize(item.summary)
            tokens -= exclude
            for tok in tokens:
                headline_for_token.setdefault(tok, item.title)
            day_tokens |= tokens

        for tok in day_tokens:
            day_moves.setdefault(tok, []).append(move)
            best = day_examples.get(tok)
            if best is None or move > best[0]:
                day_examples[tok] = (move, headline_for_token.get(tok, ""))

    if not all_moves:
        return []

    baseline = sum(all_moves) / len(all_moves)
    if baseline == 0:
        return []

    results: list[Buzzword] = []
    for word, moves in day_moves.items():
        if len(moves) < min_occurrences:
            continue
        avg_move = sum(moves) / len(moves)
        lift = avg_move / baseline
        results.append(
            Buzzword(
                word=word,
                lift=round(lift, 2),
                occurrences=len(moves),
                avg_move_pct=round(avg_move * 100, 2),
                example_headline=day_examples[word][1],
            )
        )

    results.sort(key=lambda b: b.lift, reverse=True)
    return results[:top_n]
