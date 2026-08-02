"""Tests del motor de backtest y del split in-sample/out-of-sample.

TODO: verificar que split_in_out_sample() no mezcla fechas.
"""

import pandas as pd
import pytest
import vectorbt as vbt

from forex_bot.backtest.engine import run_backtest
from forex_bot.backtest.validation import split_in_out_sample


def test_split_in_out_sample_not_implemented_yet():
    df = pd.DataFrame({"close": range(100)})
    with pytest.raises(NotImplementedError):
        split_in_out_sample(df, in_sample_ratio=0.7)


def _make_df_and_signals():
    """10 barras diarias con una entrada larga (día 3) que sale en TP/
    señal (día 5) y una entrada corta (día 5) que sale (día 8)."""
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "close": [1.10, 1.09, 1.08, 1.07, 1.12, 1.13, 1.14, 1.09, 1.08, 1.11],
    }, index=idx)
    signals = pd.DataFrame({
        "long_entries":  [False, False, True,  False, False, False, False, True,  False, False],
        "long_exits":    [False, False, False, False, True,  False, False, False, False, True],
        "short_entries": [False, False, False, False, True,  False, False, False, False, True],
        "short_exits":   [False, False, True,  False, False, False, False, True,  False, False],
    }, index=idx)
    return df, signals


def test_run_backtest_returns_vectorbt_portfolio():
    df, signals = _make_df_and_signals()
    pf = run_backtest(df, signals, initial_capital=10_000)
    assert isinstance(pf, vbt.Portfolio)


def test_run_backtest_uses_initial_capital():
    df, signals = _make_df_and_signals()
    pf = run_backtest(df, signals, initial_capital=10_000)
    assert pf.init_cash == 10_000


def test_run_backtest_executes_trades_from_signals():
    df, signals = _make_df_and_signals()
    pf = run_backtest(df, signals, initial_capital=10_000)
    # 2 entradas -> al menos 2 operaciones registradas
    assert pf.trades.count() >= 2


def test_run_backtest_applies_stop_loss_and_take_profit():
    df, signals = _make_df_and_signals()
    # sin stops
    pf_no_stops = run_backtest(df, signals, initial_capital=10_000)
    # con stops muy ajustados, debería forzar salidas distintas
    pf_with_stops = run_backtest(
        df, signals, initial_capital=10_000, stop_loss=0.005, take_profit=0.01
    )
    assert not pf_no_stops.trades.records_readable["Exit Timestamp"].equals(
        pf_with_stops.trades.records_readable["Exit Timestamp"]
    )


def test_run_backtest_applies_fees():
    df, signals = _make_df_and_signals()
    pf_no_fees = run_backtest(df, signals, initial_capital=10_000, fees=0.0)
    pf_with_fees = run_backtest(df, signals, initial_capital=10_000, fees=0.001)
    assert pf_with_fees.final_value() < pf_no_fees.final_value()


def test_run_backtest_missing_close_column_raises():
    df, signals = _make_df_and_signals()
    df = df.drop(columns=["close"])
    with pytest.raises(ValueError, match="close"):
        run_backtest(df, signals, initial_capital=10_000)


def test_run_backtest_missing_signal_column_raises():
    df, signals = _make_df_and_signals()
    signals = signals.drop(columns=["long_exits"])
    with pytest.raises(ValueError, match="long_exits"):
        run_backtest(df, signals, initial_capital=10_000)


def test_run_backtest_mismatched_index_raises():
    df, signals = _make_df_and_signals()
    signals.index = signals.index + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="índice"):
        run_backtest(df, signals, initial_capital=10_000)
