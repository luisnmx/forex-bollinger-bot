"""Tests de la tabla de reglas del Bollinger Bounce."""

import pandas as pd

from forex_bot.strategy.bollinger_bounce import generate_signals


def _make_df(close, bb_upper=1.05, bb_lower=0.95):
    return pd.DataFrame({
        "close": [close],
        "bb_upper": [bb_upper],
        "bb_lower": [bb_lower],
    })


def test_generate_signals_columns():
    df = _make_df(close=1.0)
    signals = generate_signals(df)
    assert list(signals.columns) == ["long_entries", "long_exits", "short_entries", "short_exits"]


def test_touch_lower_band_triggers_long_entry_and_short_exit():
    df = _make_df(close=0.90)  # por debajo de bb_lower=0.95
    signals = generate_signals(df)
    row = signals.iloc[0]
    assert row["long_entries"] == True
    assert row["short_exits"] == True
    assert row["long_exits"] == False
    assert row["short_entries"] == False


def test_touch_upper_band_triggers_short_entry_and_long_exit():
    df = _make_df(close=1.10)  # por encima de bb_upper=1.05
    signals = generate_signals(df)
    row = signals.iloc[0]
    assert row["short_entries"] == True
    assert row["long_exits"] == True
    assert row["long_entries"] == False
    assert row["short_exits"] == False


def test_price_inside_bands_no_signal():
    df = _make_df(close=1.00)  # entre 0.95 y 1.05
    signals = generate_signals(df)
    assert not signals.iloc[0].any()
