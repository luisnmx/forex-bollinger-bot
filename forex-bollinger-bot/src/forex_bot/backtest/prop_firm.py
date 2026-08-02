"""Simulación de reglas de evaluación de cuenta de fondeo ("prop firm").

Reglas modeladas (formato genérico "2-Step" tipo FundingPips, según lo
indicado por el usuario):
    - Objetivo de beneficio: 6% en Fase 1, 6% en Fase 2.
    - Mínimo de días operados: 1 día hábil por fase.
    - Regla de consistencia: ningún día puede representar más del 35%
      de la ganancia total obtenida.
    - Pérdida máxima total: 6% del saldo inicial.
    - Pérdida máxima diaria: 3% del saldo.

Supuestos importantes (revisar contra las reglas EXACTAS de la prop
firm elegida — varían entre firms, y a veces entre Fase 1 y Fase 2):

    1. Drawdown total ESTÁTICO: se calcula como
       initial_capital * (1 - max_total_drawdown_pct), NO como un
       trailing drawdown sobre el pico de equity alcanzado. Algunas
       firms usan trailing drawdown; si esa es la regla real, este
       módulo necesita un ajuste.

    2. Drawdown diario sobre el balance al INICIO del día, no sobre el
       equity intradía. Como el bot opera con velas diarias, no hay
       forma de detectar un breach intradía que se recupera antes del
       cierre de la vela — esto es una aproximación optimista.

    3. "Día operado" = día en el que el PnL diario fue distinto de 0
       (hubo una posición abierta generando cambios de equity ese día).

    4. Regla de consistencia: máxima ganancia de un solo día dividido
       la ganancia neta total acumulada hasta el momento en que se
       alcanza el objetivo. Si el objetivo se alcanza pero la
       consistencia no se cumple todavía, la simulación sigue
       corriendo (no se corta ahí) — se sigue evaluando día a día
       hasta que se cumplan todas las condiciones a la vez, o hasta
       que se acaben los datos o se rompa un límite de drawdown.
"""

from __future__ import annotations

import pandas as pd


def daily_pnl_from_portfolio(pf, initial_capital: float) -> pd.Series:
    """Extrae el PnL diario (variación de equity, incluyendo posiciones
    abiertas marcadas a mercado) de un vectorbt.Portfolio con datos
    diarios.

    Args:
        pf: vectorbt.Portfolio devuelto por forex_bot.backtest.engine.run_backtest().
        initial_capital: capital inicial usado en ese backtest.

    Returns:
        pd.Series de PnL diario, mismo índice que el backtest.
    """
    equity = pf.value()
    pnl = equity.diff()
    pnl.iloc[0] = equity.iloc[0] - initial_capital
    return pnl


def simulate_prop_firm_challenge(
    daily_pnl: pd.Series,
    initial_capital: float,
    profit_target_pct: float = 0.06,
    max_daily_loss_pct: float = 0.03,
    max_total_drawdown_pct: float = 0.06,
    max_daily_profit_share_pct: float = 0.35,
    min_trading_days: int = 1,
) -> dict:
    """Simula un challenge de cuenta de fondeo día por día sobre una
    serie de PnL diario, cortando en el primer evento que decide el
    resultado (breach de drawdown, o objetivo alcanzado cumpliendo
    todas las reglas).

    Args:
        daily_pnl: serie de PnL diario (ver daily_pnl_from_portfolio()).
        initial_capital: balance inicial de la cuenta.
        profit_target_pct: objetivo de beneficio, como fracción (0.06 = 6%).
        max_daily_loss_pct: pérdida máxima diaria permitida, como
            fracción del balance al inicio de ese día.
        max_total_drawdown_pct: pérdida máxima total permitida, como
            fracción de initial_capital (drawdown estático, ver nota
            del módulo).
        max_daily_profit_share_pct: máxima proporción de la ganancia
            neta total que un solo día puede representar.
        min_trading_days: mínimo de días con PnL != 0 antes de poder
            dar el challenge por aprobado.

    Returns:
        dict con: passed (bool), reason (str: "passed", "max_daily_loss",
        "max_total_drawdown" o "target_not_reached"), date (fecha del
        evento que decidió el resultado, o la última fecha de los
        datos si nunca se alcanzó el objetivo), final_balance,
        net_profit_pct, trading_days.

    Raises:
        ValueError: si initial_capital no es positivo, o si algún
            porcentaje no está en (0, 1].
    """
    if initial_capital <= 0:
        raise ValueError("initial_capital debe ser positivo")

    for name, pct in (
        ("profit_target_pct", profit_target_pct),
        ("max_daily_loss_pct", max_daily_loss_pct),
        ("max_total_drawdown_pct", max_total_drawdown_pct),
        ("max_daily_profit_share_pct", max_daily_profit_share_pct),
    ):
        if not 0 < pct <= 1:
            raise ValueError(f"{name} debe estar entre 0 y 1, recibido: {pct}")

    balance = initial_capital
    total_dd_floor = initial_capital * (1 - max_total_drawdown_pct)
    trading_days = 0
    daily_profits: list[float] = []

    for date, pnl in daily_pnl.items():
        day_start_balance = balance
        balance += pnl

        if pnl != 0:
            trading_days += 1
        if pnl > 0:
            daily_profits.append(pnl)

        daily_loss_floor = day_start_balance * (1 - max_daily_loss_pct)
        if balance < daily_loss_floor:
            return _build_result(False, "max_daily_loss", date, balance, initial_capital, trading_days)

        if balance < total_dd_floor:
            return _build_result(False, "max_total_drawdown", date, balance, initial_capital, trading_days)

        net_profit = balance - initial_capital
        target_reached = net_profit >= initial_capital * profit_target_pct

        if target_reached and trading_days >= min_trading_days:
            max_share = (max(daily_profits) / net_profit) if (net_profit > 0 and daily_profits) else 1.0
            if max_share <= max_daily_profit_share_pct:
                return _build_result(True, "passed", date, balance, initial_capital, trading_days)
            # objetivo alcanzado pero la regla de consistencia todavía
            # no se cumple: no se corta acá, se sigue simulando

    last_date = daily_pnl.index[-1] if len(daily_pnl) else None
    return _build_result(False, "target_not_reached", last_date, balance, initial_capital, trading_days)


def evaluate_two_phase_challenge(
    daily_pnl_phase1: pd.Series,
    daily_pnl_phase2: pd.Series,
    initial_capital: float,
    **rule_kwargs,
) -> dict:
    """Evalúa Fase 1 y, si se aprueba, Fase 2 — con el balance
    reseteado a initial_capital al empezar la Fase 2, como es habitual
    en los challenges de dos fases.

    Asume las mismas reglas (profit_target_pct, etc.) para ambas fases,
    que es lo típico en modelos "2-Step" (6% / 6%). Si tu prop firm usa
    reglas distintas por fase, llamá a simulate_prop_firm_challenge()
    dos veces por separado con distintos kwargs en cada llamada.

    Args:
        daily_pnl_phase1: PnL diario durante la Fase 1.
        daily_pnl_phase2: PnL diario durante la Fase 2.
        initial_capital: balance inicial (igual en ambas fases).
        **rule_kwargs: se pasan tal cual a simulate_prop_firm_challenge()
            para ambas fases.

    Returns:
        dict con: passed (bool), failed_phase (1, 2 o None), phase1
        (resultado de Fase 1), phase2 (resultado de Fase 2, o None si
        no se llegó a intentar por no pasar Fase 1).
    """
    phase1 = simulate_prop_firm_challenge(daily_pnl_phase1, initial_capital, **rule_kwargs)
    if not phase1["passed"]:
        return {"passed": False, "failed_phase": 1, "phase1": phase1, "phase2": None}

    phase2 = simulate_prop_firm_challenge(daily_pnl_phase2, initial_capital, **rule_kwargs)
    if not phase2["passed"]:
        return {"passed": False, "failed_phase": 2, "phase1": phase1, "phase2": phase2}

    return {"passed": True, "failed_phase": None, "phase1": phase1, "phase2": phase2}


def _build_result(passed: bool, reason: str, date, balance: float, initial_capital: float, trading_days: int) -> dict:
    return {
        "passed": passed,
        "reason": reason,
        "date": date,
        "final_balance": balance,
        "net_profit_pct": (balance - initial_capital) / initial_capital,
        "trading_days": trading_days,
    }
