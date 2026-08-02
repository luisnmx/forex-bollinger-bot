"""Reglas del modelo Bollinger Bounce (operar en rango).

Entrada largo:   cierre de vela toca/cruza banda inferior
Salida largo:    cierre de vela toca/cruza banda superior
Entrada corto:   cierre de vela toca/cruza banda superior
Salida corto:    cierre de vela toca/cruza banda inferior

Nota: como es una estrategia siempre-en-mercado (rota entre largo y
corto), long_exits coincide con short_entries, y short_exits coincide
con long_entries. Esto es intencional: al tocar la banda superior se
cierra el largo y se abre el corto en la misma señal.
"""

import pandas as pd


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Genera señales de entrada/salida a partir de un DataFrame con
    columnas: close, bb_upper, bb_lower.

    Returns:
        DataFrame con columnas booleanas: long_entries, long_exits,
        short_entries, short_exits — listas para vectorbt.Portfolio.from_signals().
    """
    close = df["close"]
    bb_upper = df["bb_upper"]
    bb_lower = df["bb_lower"]

    touches_lower = close <= bb_lower
    touches_upper = close >= bb_upper

    return pd.DataFrame({
        "long_entries": touches_lower,
        "long_exits": touches_upper,
        "short_entries": touches_upper,
        "short_exits": touches_lower,
    })
