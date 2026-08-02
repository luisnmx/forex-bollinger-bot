"""Motor de backtest.

Usa vectorbt.Portfolio.from_signals() para simular la ejecución de las
señales generadas por la estrategia (forex_bot.strategy) sobre el
histórico de precios, incluyendo stop_loss, take_profit y costes de
transacción.

Nota sobre costes de transacción: en Forex el coste real es el spread
bid/ask, no una comisión explícita como en acciones. vectorbt no tiene
un concepto nativo de spread, así que se modela como `fees`: un
porcentaje del valor de cada operación equivalente al spread típico
del par (ej. para EUR/GBP con spread de ~1.5 pips a 4 decimales,
fees ≈ 0.00015). `slippage` es aparte y se suma al coste efectivo de
entrada/salida. Dejar ambos en su valor por defecto (0.0) simula un
mercado sin fricción, útil como referencia, pero NO representativo de
condiciones reales: siempre correr también con costes realistas antes
de sacar conclusiones sobre la rentabilidad del modelo.
"""

from __future__ import annotations

import pandas as pd
import vectorbt as vbt

REQUIRED_SIGNAL_COLUMNS = ("long_entries", "long_exits", "short_entries", "short_exits")


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    fees: float = 0.0,
    slippage: float = 0.0,
    size: float | None = None,
    freq: str = "1D",
) -> vbt.Portfolio:
    """Corre el backtest y devuelve el objeto de resultados (portfolio).

    Args:
        df: DataFrame con al menos la columna `close`, indexado por fecha
            (ver forex_bot.data.loader.load_processed_data).
        signals: DataFrame con columnas booleanas long_entries, long_exits,
            short_entries, short_exits, con el mismo índice que `df`
            (ver forex_bot.strategy.bollinger_bounce.generate_signals).
        initial_capital: capital inicial de la cuenta.
        stop_loss: stop loss como fracción del precio de entrada
            (ej. 0.001 = 0.1%). None desactiva el stop loss.
        take_profit: take profit como fracción del precio de entrada.
            None desactiva el take profit.
        fees: coste de transacción como fracción del valor de cada
            operación. Ver nota sobre spread en el docstring del módulo.
        slippage: deslizamiento como fracción del precio, aplicado
            además de `fees`.
        size: tamaño fijo de cada operación en unidades de la divisa
            base (ej. lot_size de config/settings.yaml). None usa todo
            el capital disponible en cada entrada (comportamiento por
            defecto de vectorbt).
        freq: frecuencia del índice temporal, usada por vectorbt para
            anualizar métricas como el Sharpe ratio ("1D" para diario,
            debe coincidir con data.timeframe de config/settings.yaml).

    Returns:
        vectorbt.Portfolio con el resultado de la simulación, del cual
        se derivan las métricas en forex_bot.backtest.metrics.

    Raises:
        ValueError: si a `df` le falta la columna `close`, a `signals`
            le falta alguna columna requerida, o los índices de `df` y
            `signals` no coinciden.
    """
    if "close" not in df.columns:
        raise ValueError("df debe tener una columna 'close'")

    missing = [c for c in REQUIRED_SIGNAL_COLUMNS if c not in signals.columns]
    if missing:
        raise ValueError(f"signals no tiene las columnas requeridas: {missing}")

    if not df.index.equals(signals.index):
        raise ValueError("df y signals deben compartir el mismo índice (fechas)")

    return vbt.Portfolio.from_signals(
        close=df["close"],
        entries=signals["long_entries"],
        exits=signals["long_exits"],
        short_entries=signals["short_entries"],
        short_exits=signals["short_exits"],
        size=size,
        sl_stop=stop_loss,
        tp_stop=take_profit,
        fees=fees,
        slippage=slippage,
        init_cash=initial_capital,
        freq=freq,
    )
