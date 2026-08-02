"""Motor de backtest.

TODO: usar vectorbt (o backtrader) para simular la ejecución de las
señales generadas por la estrategia sobre el histórico, incluyendo
stop_loss y take_profit una vez definidos en la fase de optimización.
"""

import pandas as pd


def run_backtest(df: pd.DataFrame, signals: pd.Series, initial_capital: float,
                  stop_loss: float | None = None, take_profit: float | None = None):
    """Corre el backtest y devuelve el objeto de resultados (portfolio).

    Returns:
        Objeto de resultados del framework de backtesting elegido
        (ej. vectorbt.Portfolio), del cual se derivan las métricas.
    """
    raise NotImplementedError("TODO: implementar con vectorbt.Portfolio.from_signals()")
