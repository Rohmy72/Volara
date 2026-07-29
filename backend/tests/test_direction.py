import pandas as pd

from app.services.news_beta import compute_directional_bias

DAYS = pd.bdate_range("2024-01-01", periods=12)
NEWS_DAYS = set(DAYS[:8])


def _bias(values):
    return compute_directional_bias(pd.Series(values, index=DAYS), NEWS_DAYS)


def test_upside_skew():
    r = _bias([0.03, 0.02, 0.04, 0.01, -0.01, 0.02, 0.03, 0.02] + [0.0] * 4)
    assert r["direction_label"] == "Upside-skewed"
    assert r["n_news_up_days"] == 7
    assert r["n_news_down_days"] == 1
    assert r["news_day_up_share"] == 0.875
    assert r["news_day_avg_signed_pct"] > 0


def test_downside_skew():
    r = _bias([-0.03, -0.02, -0.05, -0.01, 0.01, -0.02, -0.04, -0.03] + [0.0] * 4)
    assert r["direction_label"] == "Downside-skewed"
    assert r["n_news_down_days"] == 7
    assert r["news_day_avg_signed_pct"] < 0
    assert "fell on 7 of 8 news days" in r["direction_explanation"]


def test_two_sided():
    r = _bias([0.03, -0.02, 0.04, -0.03, 0.02, -0.02, 0.03, -0.03] + [0.0] * 4)
    assert r["direction_label"] == "Two-sided"
    assert r["n_news_up_days"] == r["n_news_down_days"] == 4


def test_magnitude_asymmetry_is_called_out():
    """An evenly-split stock whose losses dwarf its gains should still say so."""
    r = _bias([0.01, -0.05, 0.01, -0.06, 0.01, -0.05, 0.012, -0.05] + [0.0] * 4)
    assert r["direction_label"] == "Two-sided"
    assert "Down reactions are larger" in r["direction_explanation"]
    assert r["avg_down_move_pct"] < 0 < r["avg_up_move_pct"]


def test_flat_moves_below_threshold_are_not_directional():
    r = _bias([0.0001] * 8 + [0.0] * 4)
    assert r["direction_label"] is None
    assert r["n_news_up_days"] == 0


def test_no_news_days():
    r = compute_directional_bias(pd.Series([0.02] * 12, index=DAYS), set())
    assert r["direction_label"] is None
