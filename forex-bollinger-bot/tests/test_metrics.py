"""Tests de las métricas de robustez del modelo."""

import math

import pytest

from forex_bot.backtest.metrics import (
    profit_factor,
    recovery_factor,
    sharpe_ratio,
    value_at_risk,
)


# ---------------------------------------------------------------------------
# recovery_factor
# ---------------------------------------------------------------------------

def test_recovery_factor_basic():
    assert recovery_factor(net_profit=8580, max_drawdown=1000) == 8.58


def test_recovery_factor_zero_drawdown_raises():
    with pytest.raises(ValueError, match="0"):
        recovery_factor(net_profit=1000, max_drawdown=0)


def test_recovery_factor_negative_drawdown_raises():
    with pytest.raises(ValueError, match="absoluto"):
        recovery_factor(net_profit=1000, max_drawdown=-50)


# ---------------------------------------------------------------------------
# profit_factor
# ---------------------------------------------------------------------------

def test_profit_factor_basic():
    assert profit_factor(gross_profit=2310, gross_loss=-1000) == pytest.approx(2.31)


def test_profit_factor_accepts_positive_gross_loss():
    assert profit_factor(gross_profit=2310, gross_loss=1000) == pytest.approx(2.31)


def test_profit_factor_no_losses_returns_inf():
    assert profit_factor(gross_profit=500, gross_loss=0) == math.inf


# ---------------------------------------------------------------------------
# sharpe_ratio
# ---------------------------------------------------------------------------

def test_sharpe_ratio_basic():
    returns = [0.01, -0.005, 0.02, 0.0, 0.015]
    result = sharpe_ratio(returns)
    # mean=0.008, std(ddof=1)=0.010380... -> 0.008/0.010380 = 0.7708
    assert result == pytest.approx(0.7716, abs=1e-3)


def test_sharpe_ratio_annualized_scales_by_sqrt_periods():
    returns = [0.01, -0.005, 0.02, 0.0, 0.015]
    raw = sharpe_ratio(returns)
    annualized = sharpe_ratio(returns, annualize_periods=252)
    assert annualized == pytest.approx(raw * math.sqrt(252))


def test_sharpe_ratio_too_few_observations_raises():
    with pytest.raises(ValueError, match="2 observaciones"):
        sharpe_ratio([0.01])


def test_sharpe_ratio_zero_std_raises():
    with pytest.raises(ValueError, match="desviación estándar"):
        sharpe_ratio([0.01, 0.01, 0.01])


# ---------------------------------------------------------------------------
# value_at_risk
# ---------------------------------------------------------------------------

def test_value_at_risk_matches_thesis_table_eur_sek():
    # Tabla 4 de la tesis (EUR/SEK): capital=10000, sigma=7.81%,
    # confianza=95%, horizonte=21 días -> VaR ~= 372.09 (la tesis usa
    # z=1.65 redondeado; nosotros usamos el z exacto de la normal
    # (1.6449), de ahí la tolerancia relativa en vez de exacta)
    result = value_at_risk(capital=10_000, sigma=0.0781, confidence=0.95, horizon_days=21)
    assert result == pytest.approx(372.09, rel=0.01)


def test_value_at_risk_matches_thesis_table_gbp_sek():
    # Tabla 4 de la tesis (GBP/SEK): sigma=11.44% -> VaR ~= 545.07
    result = value_at_risk(capital=10_000, sigma=0.1144, confidence=0.95, horizon_days=21)
    assert result == pytest.approx(545.07, rel=0.01)


def test_value_at_risk_higher_confidence_gives_higher_var():
    var_95 = value_at_risk(capital=10_000, sigma=0.10, confidence=0.95)
    var_99 = value_at_risk(capital=10_000, sigma=0.10, confidence=0.99)
    assert var_99 > var_95


def test_value_at_risk_invalid_confidence_raises():
    with pytest.raises(ValueError, match="confidence"):
        value_at_risk(capital=10_000, sigma=0.10, confidence=1.5)
