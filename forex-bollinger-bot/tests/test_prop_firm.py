"""Tests de la simulación de reglas de cuenta de fondeo."""

import pandas as pd
import pytest

from forex_bot.backtest.prop_firm import (
    evaluate_two_phase_challenge,
    simulate_prop_firm_challenge,
)


def _pnl_series(values, start="2024-01-01"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=idx)


# ---------------------------------------------------------------------------
# caso limpio: pasa sin romper ninguna regla
# ---------------------------------------------------------------------------

def test_passes_when_target_reached_cleanly():
    # 10000 inicial, objetivo 6% = 600. Ganancias repartidas en varios
    # días, ninguno concentra más del 35%.
    pnl = _pnl_series([100, 100, 100, 100, 100, 100, 100])  # 700 acumulado, día 7 llega a 600
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000)
    assert result["passed"] is True
    assert result["reason"] == "passed"
    assert result["trading_days"] == 6  # se corta el día que llega a 600 (día 6, PnL acumulado=600)


def test_final_balance_and_net_profit_pct_correct():
    pnl = _pnl_series([200] * 4)  # 800 en 4 días, objetivo 600 se alcanza en día 3
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000)
    assert result["passed"] is True
    assert result["final_balance"] == pytest.approx(10_600)
    assert result["net_profit_pct"] == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# pérdida máxima diaria
# ---------------------------------------------------------------------------

def test_fails_on_max_daily_loss():
    # día 1: -3.5% de 10000 = -350, rompe el límite de 3%
    pnl = _pnl_series([-350, 1000, 1000])
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000, max_daily_loss_pct=0.03)
    assert result["passed"] is False
    assert result["reason"] == "max_daily_loss"
    assert result["date"] == pnl.index[0]


def test_daily_loss_ok_if_under_limit():
    pnl = _pnl_series([-299, 700])  # -2.99% no rompe el 3%
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000, max_daily_loss_pct=0.03)
    assert result["reason"] != "max_daily_loss"


# ---------------------------------------------------------------------------
# pérdida máxima total
# ---------------------------------------------------------------------------

def test_fails_on_max_total_drawdown():
    # pérdidas acumuladas que superan el 6% total, cada una bajo el 3% diario
    pnl = _pnl_series([-250, -250, -250, -250, -250])  # -5% en 5 días, y en total supera 6%? veamos
    result = simulate_prop_firm_challenge(
        pnl, initial_capital=10_000, max_daily_loss_pct=0.10, max_total_drawdown_pct=0.06
    )
    assert result["passed"] is False
    assert result["reason"] == "max_total_drawdown"


# ---------------------------------------------------------------------------
# objetivo no alcanzado
# ---------------------------------------------------------------------------

def test_target_not_reached_if_data_runs_out():
    pnl = _pnl_series([50, 50, 50])  # 150 total, muy por debajo del 6% (600)
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000)
    assert result["passed"] is False
    assert result["reason"] == "target_not_reached"
    assert result["date"] == pnl.index[-1]


# ---------------------------------------------------------------------------
# días mínimos operados
# ---------------------------------------------------------------------------

def test_does_not_pass_before_min_trading_days_even_if_target_reached():
    # un solo día enorme alcanza el objetivo, pero se pide mínimo 3 días
    pnl = _pnl_series([700, 0, 0])
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000, min_trading_days=3)
    # no hay más días con pnl != 0 después, así que nunca llega a 3 días operados
    assert result["passed"] is False
    assert result["reason"] == "target_not_reached"


# ---------------------------------------------------------------------------
# regla de consistencia (ningún día > 35% de la ganancia total)
# ---------------------------------------------------------------------------

def test_fails_consistency_when_one_day_dominates_and_never_recovers():
    # un solo día de 700 (>6%) representa el 100% de la ganancia -> rompe consistencia
    pnl = _pnl_series([700, 0, 0])
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000, max_daily_profit_share_pct=0.35)
    assert result["passed"] is False
    assert result["reason"] == "target_not_reached"


def test_passes_once_consistency_restored_after_dominant_day():
    # día 1: 700 (domina, 100% del total). Se sigue operando y ganando
    # hasta que ese día ya no represente más del 35% del acumulado:
    # 700 / x <= 0.35  =>  x >= 2000  =>  con +300/día hacen falta 5
    # días más (700 + 5*300 = 2200, 700/2200 = 0.318 <= 0.35)
    pnl = _pnl_series([700, 300, 300, 300, 300, 300])
    result = simulate_prop_firm_challenge(pnl, initial_capital=10_000, max_daily_profit_share_pct=0.35)
    assert result["passed"] is True
    assert result["reason"] == "passed"


# ---------------------------------------------------------------------------
# validación de parámetros
# ---------------------------------------------------------------------------

def test_invalid_initial_capital_raises():
    with pytest.raises(ValueError, match="initial_capital"):
        simulate_prop_firm_challenge(_pnl_series([1]), initial_capital=0)


def test_invalid_pct_raises():
    with pytest.raises(ValueError, match="profit_target_pct"):
        simulate_prop_firm_challenge(_pnl_series([1]), initial_capital=10_000, profit_target_pct=1.5)


# ---------------------------------------------------------------------------
# evaluate_two_phase_challenge
# ---------------------------------------------------------------------------

def test_two_phase_passes_when_both_phases_pass():
    phase1 = _pnl_series([100] * 7)
    phase2 = _pnl_series([100] * 7, start="2024-06-01")
    result = evaluate_two_phase_challenge(phase1, phase2, initial_capital=10_000)
    assert result["passed"] is True
    assert result["failed_phase"] is None
    assert result["phase1"]["passed"] is True
    assert result["phase2"]["passed"] is True


def test_two_phase_fails_phase1_does_not_run_phase2():
    phase1 = _pnl_series([10] * 3)  # nunca llega al objetivo
    phase2 = _pnl_series([100] * 7, start="2024-06-01")
    result = evaluate_two_phase_challenge(phase1, phase2, initial_capital=10_000)
    assert result["passed"] is False
    assert result["failed_phase"] == 1
    assert result["phase2"] is None


def test_two_phase_fails_phase2_after_passing_phase1():
    phase1 = _pnl_series([100] * 7)
    phase2 = _pnl_series([-350], start="2024-06-01")  # rompe max_daily_loss en fase 2
    result = evaluate_two_phase_challenge(phase1, phase2, initial_capital=10_000)
    assert result["passed"] is False
    assert result["failed_phase"] == 2
    assert result["phase1"]["passed"] is True
    assert result["phase2"]["passed"] is False
