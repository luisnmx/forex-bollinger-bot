"""Test de integración del pipeline completo (scripts/run_backtest.py).

scripts/ no es parte del paquete instalable (pythonpath=src en
pytest.ini), así que se importa por ruta de archivo en vez de por
nombre de paquete.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "run_backtest.py"


def _load_run_backtest_module():
    spec = importlib.util.spec_from_file_location("run_backtest_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rb():
    return _load_run_backtest_module()


@pytest.fixture
def synthetic_config(tmp_path):
    """Escribe un CSV 'procesado' sintético y arma un dict de config
    que apunta a carpetas temporales, para no depender de red ni de
    datos reales."""
    processed_dir = tmp_path / "processed"
    raw_dir = tmp_path / "raw"
    processed_dir.mkdir()
    raw_dir.mkdir()

    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2020-01-01", periods=300)
    price = 1.10 + np.cumsum(rng.normal(0, 0.001, len(idx)))
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
            "start_date": "2020-01-01",
            "end_date": None,
            "raw_path": str(raw_dir),
            "processed_path": str(processed_dir),
        },
        "strategy": {"name": "bollinger_bounce", "bollinger": {"period": 20, "std_dev": 2.0}},
        "validation": {"in_sample_ratio": 0.7},
        "account": {"initial_capital": 10_000, "lot_size": 1_000},
    }


def test_run_pipeline_end_to_end(rb, synthetic_config):
    results = rb.run_pipeline(synthetic_config)

    assert results["pair"] == "EURGBP=X"
    assert isinstance(results["net_return"], float)
    assert results["max_drawdown"] >= 0
    assert results["profit_factor"] >= 0


def test_run_pipeline_profit_factor_matches_vectorbt_stats(rb, synthetic_config):
    """profit_factor propio debe coincidir con el de pf.stats() de
    vectorbt (ambos calculados solo sobre operaciones cerradas)."""
    results = rb.run_pipeline(synthetic_config)
    pf = results["portfolio"]
    assert results["profit_factor"] == pytest.approx(pf.trades.closed.profit_factor(), rel=1e-6)


def test_run_pipeline_uses_processed_data_without_fetching(rb, synthetic_config, monkeypatch):
    """Si ya hay datos procesados, no debe intentar descargar nada."""

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("no debería llamar a fetch_historical_data si ya hay datos procesados")

    monkeypatch.setattr(rb, "fetch_historical_data", _fail_if_called)
    rb.run_pipeline(synthetic_config)  # no debe lanzar


def test_print_results_does_not_raise(rb, synthetic_config, capsys):
    results = rb.run_pipeline(synthetic_config)
    rb.print_results(results)
    captured = capsys.readouterr()
    assert "EURGBP=X" in captured.out
    assert "Profit factor" in captured.out
