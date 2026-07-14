import pandas as pd

from app.services.buzzwords import extract_buzzwords
from app.services.news_sources import NewsItem


def _item(title, summary=""):
    return NewsItem(
        title=title,
        source="Test",
        url="https://example.com",
        published_at=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
        summary=summary,
    )


def test_high_move_word_gets_high_lift():
    dates = pd.bdate_range("2024-01-02", periods=10)

    news_day_map = {
        dates[0]: [_item("Company issues major recall of flagship product")],
        dates[2]: [_item("Analyst recall concerns weigh on shares")],
        dates[4]: [_item("Company announces routine quarterly dividend")],
        dates[6]: [_item("Company hosts investor day webinar")],
        dates[8]: [_item("Company updates logo on website")],
    }

    # Big abnormal moves on the "recall" days, small moves elsewhere.
    abnormal = pd.Series(0.001, index=dates)
    abnormal[dates[0]] = 0.08
    abnormal[dates[2]] = 0.07

    buzzwords = extract_buzzwords(
        news_day_map, abnormal, ticker="TEST", company_name="Test Co", min_occurrences=2
    )

    words = {b.word: b for b in buzzwords}
    assert "recall" in words
    assert words["recall"].lift > 2
    assert words["recall"].occurrences == 2


def test_excludes_ticker_and_stopwords():
    dates = pd.bdate_range("2024-01-02", periods=4)
    news_day_map = {
        dates[0]: [_item("TEST stock rises on the news today")],
        dates[2]: [_item("TEST stock falls on the news today")],
    }
    abnormal = pd.Series([0.05, 0.01, 0.05, 0.01], index=dates)

    buzzwords = extract_buzzwords(
        news_day_map, abnormal, ticker="TEST", min_occurrences=2
    )

    words = {b.word for b in buzzwords}
    assert "test" not in words
    assert "the" not in words
    assert "stock" not in words
    assert "news" not in words


def test_empty_input_returns_empty_list():
    assert extract_buzzwords({}, pd.Series(dtype=float), ticker="TEST") == []
