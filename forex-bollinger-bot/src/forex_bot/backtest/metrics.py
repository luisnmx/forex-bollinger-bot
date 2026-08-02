"""Métricas de robustez del modelo.

Umbrales de referencia (sección IV.3.3 de la tesis de M. Sobrepere
Delgado, 2015, y la literatura de evaluación de modelos):
    recovery_factor > 6
    profit_factor   > 2
    sharpe_ratio    > 2

Estas funciones toman valores ya calculados (net_profit, max_drawdown,
etc.), no el objeto vectorbt.Portfolio directamente, para mantenerlas
simples y testeables por separado. Para conectarlas con el resultado
de forex_bot.backtest.engine.run_backtest():

    pf = run_backtest(...)
    pnl = pf.trades.pnl.to_pandas() if hasattr(pf.trades.pnl, "to_pandas") else pf.trades.pnl

    recovery_factor(pf.total_profit(), abs(pf.max_drawdown()))
    profit_factor(pnl[pnl > 0].sum(), pnl[pnl < 0].sum())
    sharpe_ratio(pf.returns(), annualize_periods=252)  # freq diaria
    value_at_risk(pf.init_cash, pf.returns().std() * (252 ** 0.5))
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np


def recovery_factor(net_profit: float, max_drawdown: float) -> float:
    """Relación entre beneficio neto y máximo drawdown.

    Un modelo se considera bueno si recovery_factor > 6 (IV.3.3).

    Args:
        net_profit: beneficio neto total del backtest.
        max_drawdown: máximo drawdown, en valor absoluto (positivo).

    Raises:
        ValueError: si max_drawdown es negativo (debe pasarse en
            valor absoluto) o 0 (el ratio no está definido).
    """
    if max_drawdown < 0:
        raise ValueError("max_drawdown debe pasarse en valor absoluto (positivo)")
    if max_drawdown == 0:
        raise ValueError("max_drawdown es 0, recovery_factor no está definido")
    return net_profit / max_drawdown


def profit_factor(gross_profit: float, gross_loss: float) -> float:
    """Relación entre ganancias y pérdidas brutas.

    Un modelo se considera fiable si profit_factor > 2 (no solo > 1),
    porque las comisiones reales bajan esta ratio en producción (IV.3.3).

    Args:
        gross_profit: suma de ganancias de las operaciones ganadoras
            (valor positivo).
        gross_loss: suma de pérdidas de las operaciones perdedoras;
            puede pasarse en positivo o negativo, se usa su valor
            absoluto.

    Returns:
        gross_profit / abs(gross_loss). Si gross_loss es 0 (sin
        operaciones perdedoras) devuelve float('inf').
    """
    if gross_loss == 0:
        return math.inf
    return gross_profit / abs(gross_loss)


def sharpe_ratio(
    returns,
    risk_free_rate: float = 0.0,
    annualize_periods: int | None = None,
) -> float:
    """Sharpe ratio de una serie de retornos periódicos.

    Un modelo se considera fiable si sharpe_ratio > 2 (IV.3.3).

    Args:
        returns: serie/array de retornos periódicos (ej. pf.returns()
            de vectorbt.Portfolio).
        risk_free_rate: tasa libre de riesgo, en la misma frecuencia
            que `returns` (0.0 por defecto).
        annualize_periods: si se pasa (ej. 252 para retornos diarios),
            anualiza el ratio multiplicándolo por sqrt(annualize_periods).
            None devuelve el ratio en la frecuencia original de `returns`.

    Raises:
        ValueError: si `returns` tiene menos de 2 observaciones, o si
            su desviación estándar es 0 (retornos constantes).
    """
    returns_arr = np.asarray(returns, dtype=float)
    if len(returns_arr) < 2:
        raise ValueError("returns necesita al menos 2 observaciones")

    std = returns_arr.std(ddof=1)
    if std == 0:
        raise ValueError("la desviación estándar de returns es 0, sharpe_ratio no está definido")

    ratio = (returns_arr.mean() - risk_free_rate) / std
    if annualize_periods is not None:
        ratio *= math.sqrt(annualize_periods)
    return ratio


def value_at_risk(capital: float, sigma: float, confidence: float = 0.95, horizon_days: int = 21) -> float:
    """VaR paramétrico (asume retornos normales).

    Replica el cálculo de la tesis de referencia (IV.3.3, Tabla 4):
        VaR = capital * sigma * z_confidence * sqrt(horizon_days / 252)

    Args:
        capital: capital de la cuenta.
        sigma: desviación estándar ANUAL de los retornos (ej. std de
            retornos diarios * sqrt(252)).
        confidence: nivel de confianza, ej. 0.95 o 0.99.
        horizon_days: horizonte en días hábiles (21 ≈ 1 mes, como en
            la tesis; 252 días hábiles por año).

    Returns:
        Pérdida máxima esperada, en las mismas unidades que `capital`,
        con probabilidad `confidence`, en el horizonte `horizon_days`.

    Raises:
        ValueError: si confidence no está en (0, 1).
    """
    if not 0 < confidence < 1:
        raise ValueError(f"confidence debe estar entre 0 y 1 (exclusivo), recibido: {confidence}")

    z = NormalDist().inv_cdf(confidence)
    return capital * sigma * z * math.sqrt(horizon_days / 252)
