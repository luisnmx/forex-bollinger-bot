"""Tests del cálculo de indicadores."""

import pandas as pd

from forex_bot.indicators.bollinger import bollinger_bands


def test_bollinger_bands_columns():
    close = pd.Series(range(1, 31), dtype=float)
    result = bollinger_bands(close, period=20, std_dev=2.0)
    assert list(result.columns) == ["bb_mid", "bb_upper", "bb_lower"]


def test_bollinger_bands_upper_above_lower():
    close = pd.Series(range(1, 31), dtype=float)
    result = bollinger_bands(close, period=20, std_dev=2.0)
    valid = result.dropna()
    assert (valid["bb_upper"] >= valid["bb_mid"]).all()
    assert (valid["bb_mid"] >= valid["bb_lower"]).all()


def test_bollinger_bands_constant_price_zero_width():
    # con precio constante, la desviación estándar es 0, así que las
    # tres bandas deben coincidir
    close = pd.Series([1.5] * 25)
    result = bollinger_bands(close, period=20, std_dev=2.0)
    valid = result.dropna()
    assert (valid["bb_upper"] == valid["bb_mid"]).all()
    assert (valid["bb_lower"] == valid["bb_mid"]).all()
