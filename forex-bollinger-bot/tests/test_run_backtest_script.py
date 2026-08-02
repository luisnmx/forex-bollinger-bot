"""Test de integración del grid search (scripts/run_optimization.py)."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "run_optimization.py"


def _load_run_optimization_module():
    spec = importlib.util.spec_from_file_location("run_optimization_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ro():
    return _load_run_optimization_module()


@pytest.fixture
def synthetic_config(tmp_path):
    processed_dir = tmp_path / "processed"
    raw_dir = tmp_path / "raw"
    processed_dir.mkdir()
    raw_dir.mkdir()

    # más datos que en test_run_backtest_script.py: el grid search
    # necesita suficientes operaciones en in-sample (70%) para no
    # descartar todas las combinaciones por MIN_TRADES
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2015-01-01", periods=1500)
    price = 1.10 + np.cumsum(rng.normal(0, 0.0015, len(idx)))
    df = pd.DataFrame(
        {"open": price, "high": price + 0.001, "low": price - 0.001, "close": price},
        index=idx,
    )
    df.index.name = "date"
    df.to_csv(processed_dir / "EURGBP_X.csv")

    return {
        "data": {
            "pair": "EURGBP=X",
            "timeframe": "1d",
            "start_date": "2015-01-01",
            "end_date": None,
            "raw_path": str(raw_dir),
            "processed_path": str(processed_dir),
        },
        "strategy": {"name": "bollinger_bounce", "bollinger": {"period": 20, "std_dev": 2.0}},
        "validation": {"in_sample_ratio": 0.7},
        "account": {"initial_capital": 10_000, "lot_size": 1_000},
    }


def test_optimize_only_uses_in_sample_data(ro, synthetic_config):
    """El grid search no debe tocar el tramo out-of-sample."""
    df_in, _signals_in = ro._prepare_in_sample_data(synthetic_config)

    from forex_bot.backtest.validation import split_in_out_sample
    from forex_bot.data.loader import load_processed_data
    from forex_bot.indicators.bollinger import bollinger_bands

    full_df = load_processed_data(synthetic_config["data"]["processed_path"])
    bands = bollinger_bands(full_df["close"], period=20, std_dev=2.0)
    full_df = full_df.join(bands)
    full_df_valid = full_df.loc[full_df["bb_upper"].notna()]
    expected_in, _expected_out = split_in_out_sample(full_df_valid, in_sample_ratio=0.7)

    assert df_in.index.max() == expected_in.index.max()
    assert df_in.index.max() < full_df_valid.index.max()


def test_optimize_returns_best_and_all_results(ro, synthetic_config):
    opt_results = ro.optimize(synthetic_config)

    assert "best" in opt_results
    assert "all_results" in opt_results
    assert len(opt_results["all_results"]) == len(ro.STOP_LOSS_GRID) * len(ro.TAKE_PROFIT_GRID)

    best = opt_results["best"]
    assert best["stop_loss"] in ro.STOP_LOSS_GRID
    assert best["take_profit"] in ro.TAKE_PROFIT_GRID
    assert best["n_trades"] >= ro.MIN_TRADES


def test_optimize_best_has_highest_profit_factor_among_valid(ro, synthetic_config):
    opt_results = ro.optimize(synthetic_config)
    valid = [r for r in opt_results["all_results"] if r["profit_factor"] is not None]
    assert opt_results["best"]["profit_factor"] == max(r["profit_factor"] for r in valid)


def test_optimize_raises_if_no_combination_meets_min_trades(ro, synthetic_config, monkeypatch):
    monkeypatch.setattr(ro, "MIN_TRADES", 10**9)
    with pytest.raises(RuntimeError, match="Ninguna combinación"):
        ro.optimize(synthetic_config)


def test_print_results_does_not_raise(ro, synthetic_config, capsys):
    opt_results = ro.optimize(synthetic_config)
    ro.print_results(opt_results)
    captured = capsys.readouterr()
    assert "Mejor combinación" in captured.out
    assert "out-of-sample" in captured.out