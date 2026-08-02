"""Descarga de datos históricos para el par configurado.

TODO: implementar la descarga con yfinance y guardar en data/raw
como parquet o csv, indexado por fecha.
"""

from pathlib import Path


def fetch_historical_data(pair: str, start_date: str, end_date: str | None, raw_path: str) -> Path:
    """Descarga histórico OHLC para `pair` y lo guarda en `raw_path`.

    Args:
        pair: ticker en formato yfinance, ej. "EURGBP=X".
        start_date: fecha inicial "YYYY-MM-DD".
        end_date: fecha final, None para "hasta hoy".
        raw_path: carpeta donde guardar el archivo crudo.

    Returns:
        Ruta al archivo guardado.
    """
    raise NotImplementedError("TODO: descargar con yfinance.download() y guardar en raw_path")
