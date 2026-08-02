"""Carga y limpieza de datos ya descargados, listos para backtest.

TODO: leer desde data/raw, limpiar (nulos, duplicados, gaps de fin de semana)
y guardar la versión procesada en data/processed.
"""

import pandas as pd


def load_processed_data(processed_path: str) -> pd.DataFrame:
    """Carga el dataset limpio para backtest.

    Returns:
        DataFrame con columnas: open, high, low, close, indexado por fecha.
    """
    raise NotImplementedError("TODO: leer parquet/csv desde processed_path")
