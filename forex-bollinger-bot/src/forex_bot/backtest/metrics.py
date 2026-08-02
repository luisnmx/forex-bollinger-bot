"""Métricas de robustez del modelo.

Umbrales de referencia (según la literatura de evaluación de modelos):
    recovery_factor > 6
    profit_factor   > 2
    sharpe_ratio    > 2

TODO: calcular a partir del objeto de resultados del backtest (engine.py).
"""


def recovery_factor(net_profit: float, max_drawdown: float) -> float:
    raise NotImplementedError("TODO: net_profit / max_drawdown")


def profit_factor(gross_profit: float, gross_loss: float) -> float:
    raise NotImplementedError("TODO: gross_profit / abs(gross_loss)")


def sharpe_ratio(returns, risk_free_rate: float = 0.0) -> float:
    raise NotImplementedError("TODO: (mean(returns) - risk_free_rate) / std(returns)")


def value_at_risk(capital: float, sigma: float, confidence: float = 0.95, horizon_days: int = 21) -> float:
    raise NotImplementedError("TODO: VaR paramétrico mensual")
