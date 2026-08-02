"""Test de integración del check de challenge de cuenta de fondeo
(scripts/run_prop_firm_check.py)."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "run_prop_firm_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_prop_firm_check_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rpc():
    return _load_module()


@pytest.fixture
def synthetic_config(tmp_path):
    processed_dir = tmp_path / "processed"
    raw_dir = tmp_path / "raw"
    processed_dir.mkdir()
    raw_dir.mkdir()

    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2015-01-01", periods=800)
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
        "prop_firm": {
            "profit_target_pct": 0.06,
            "max_daily_loss_pct": 0.03,
            "max_total_drawdown_pct": 0.06,
            "max_daily_profit_share_pct": 0.35,
            "min_trading_days": 1,
        },
        "account": {"initial_capital": 10_000, "lot_size": 1_000},
    }


def test_check_prop_firm_challenge_runs_end_to_end(rpc, synthetic_config):
    result = rpc.check_prop_firm_challenge(synthetic_config)
    assert "passed" in result
    assert "phase1" in result
    assert result["phase1"]["reason"] in {
        "passed", "max_daily_loss", "max_total_drawdown", "target_not_reached",
    }


def test_check_prop_firm_challenge_uses_config_rules(rpc, synthetic_config):
    synthetic_config["prop_firm"]["profit_target_pct"] = 0.50  # objetivo absurdo, no se va a alcanzar
    result = rpc.check_prop_firm_challenge(synthetic_config)
    assert result["rules"]["profit_target_pct"] == 0.50
    assert result["passed"] is False


def test_check_prop_firm_challenge_accepts_stop_loss_take_profit(rpc, synthetic_config):
    result = rpc.check_prop_firm_challenge(synthetic_config, stop_loss=0.01, take_profit=0.02)
    assert result["stop_loss"] == 0.01
    assert result["take_profit"] == 0.02


def test_print_results_does_not_raise(rpc, synthetic_config, capsys):
    result = rpc.check_prop_firm_challenge(synthetic_config)
    rpc.print_results(result)
    captured = capsys.readouterr()
    assert "CHALLENGE DE CUENTA DE FONDEO" in captured.out
    assert "Fase 1" in captured.out
    assert "Fase 2" in captured.out
