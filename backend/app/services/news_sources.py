"""Aggregates news headlines for a ticker from several free sources.

No API key is required for the default path: we combine yfinance's built-in
news feed with Google News RSS and Yahoo Finance RSS. If an Alpha Vantage key
is present (AV_KEY env var), we blend in its NEWS_SENTIMENT feed too, since it
tags articles with a per-ticker relevance score and a sentiment score — but
it is strictly optional and the app degrades gracefully without it.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
from curl_cffi import requests # type: ignore
import yfinance as yf

from app.core.config import settings

_REQUEST_TIMEOUT = 10
_USER_AGENT = "Mozilla/5.0 (compatible; StockNewsVolatilityBot/1.0)"

# Create a session that mimics a browser so Yahoo Finance doesn't block Render
session = requests.Session(impersonate="chrome")
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
})

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_summary(raw: str) -> str:
    """RSS descriptions (esp. Google News) often embed raw HTML markup and
    tracking fragments. Strip tags/entities so downstream tokenizing and the
    UI both see plain text."""
    if not raw:
        return ""
    text = _HTML_TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published_at: datetime  # timezone-aware, UTC
    summary: str = ""
    sentiment_score: float | None = None  # -1..1 when available, else None


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _from_yfinance(ticker: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        # Pass the browser session here so the news doesn't get blocked!
        raw = yf.Ticker(ticker, session=session).news or []
    except Exception:
        return items

    for entry in raw:
        # yfinance has changed its news payload shape across versions;
        # handle both the flat form and the newer {"content": {...}} form.
        content = entry.get("content", entry)
        title = content.get("title")
        if not title:
            continue
        ts = (
            content.get("pubDate")
            or entry.get("providerPublishTime")
            or content.get("providerPublishTime")
        )
        published_at = _coerce_timestamp(ts)
        if published_at is None:
            continue
        link = (
            content.get("canonicalUrl", {}).get("url")
            if isinstance(content.get("canonicalUrl"), dict)
            else entry.get("link")
        ) or ""
        publisher = (
            content.get("provider", {}).get("displayName")
            if isinstance(content.get("provider"), dict)
            else entry.get("publisher")
        ) or "Yahoo Finance"
        items.append(
            NewsItem(
                title=title,
                source=publisher,
                url=link,
                published_at=published_at,
                summary=_clean_summary(content.get("summary", "") or ""),
            )
        )
    return items


def _coerce_timestamp(ts) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _from_google_news_rss(ticker: str, company_name: str | None) -> list[NewsItem]:
    query = f"{ticker} stock"
    if company_name and company_name.upper() != ticker.upper():
        query = f"{company_name} {ticker} stock"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en" # type: ignore

    items: list[NewsItem] = []
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception:
        return items

    for entry in feed.entries:
        published_at = None
        if getattr(entry, "published_parsed", None):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) # type: ignore
        if published_at is None:
            continue
        source = ""
        if hasattr(entry, "source") and getattr(entry.source, "title", None):
            source = entry.source.title # type: ignore
        items.append(
            NewsItem(
                title=entry.get("title", ""), # type: ignore
                source=source or "Google News",
                url=entry.get("link", ""), # type: ignore
                published_at=published_at,
                summary=_clean_summary(entry.get("summary", "")), # type: ignore
            )
        )
    return items


def _from_yahoo_finance_rss(ticker: str) -> list[NewsItem]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    items: list[NewsItem] = []
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception:
        return items

    for entry in feed.entries:
        published_at = None
        if getattr(entry, "published_parsed", None):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) # type: ignore
        if published_at is None:
            continue
        items.append(
            NewsItem(
                title=entry.get("title", ""), # type: ignore
                source="Yahoo Finance",
                url=entry.get("link", ""), # type: ignore
                published_at=published_at,
                summary=_clean_summary(entry.get("summary", "")), # type: ignore
            )
        )
    return items


def _from_alpha_vantage(ticker: str) -> list[NewsItem]:
    if not settings.alpha_vantage_key:
        return []
    items: list[NewsItem] = []
    url = (
        "https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
        f"&tickers={ticker}&limit=200&apikey={settings.alpha_vantage_key}"
    )
    try:
        resp = requests.get(url, timeout=25)
        resp.raise_for_status()
        js = resp.json()
    except Exception:
        return items

    for art in js.get("feed", []):
        relevance = 0.0
        sentiment = None
        for ts in art.get("ticker_sentiment", []):
            if ts.get("ticker") == ticker.upper():
                relevance = float(ts.get("relevance_score", 0))
                sentiment = float(ts.get("ticker_sentiment_score", 0))
        if relevance < 0.3:
            continue
        raw_ts = art.get("time_published")
        try:
            published_at = datetime.strptime(raw_ts, "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except (TypeError, ValueError):
            continue
        items.append(
            NewsItem(
                title=art.get("title", ""),
                source=art.get("source", "Alpha Vantage"),
                url=art.get("url", ""),
                published_at=published_at,
                summary=_clean_summary(art.get("summary", "")),
                sentiment_score=sentiment,
            )
        )
    return items


def fetch_all_news(ticker: str, company_name: str | None = None) -> list[NewsItem]:
    """Combine every source and de-duplicate by normalized title."""
    all_items = (
        _from_yfinance(ticker)
        + _from_google_news_rss(ticker, company_name)
        + _from_yahoo_finance_rss(ticker)
        + _from_alpha_vantage(ticker)
    )

    seen: dict[str, NewsItem] = {}
    for item in all_items:
        key = _normalize_title(item.title)
        if not key:
            continue
        existing = seen.get(key)
        # Prefer the version with a longer summary (usually richer source).
        if existing is None or len(item.summary) > len(existing.summary):
            seen[key] = item

    return sorted(seen.values(), key=lambda i: i.published_at, reverse=True)