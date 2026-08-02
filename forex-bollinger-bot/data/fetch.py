"""Descarga de datos históricos para el par configurado.

Usa yfinance para bajar el histórico OHLC y lo guarda como CSV en
`raw_path`, indexado por fecha. El nombre del archivo se deriva del
ticker (ej. "EURGBP=X" -> "EURGBP_X.csv") para que loader.py pueda
encontrarlo sin ambigüedad.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


def _sanitize_filename(pair: str) -> str:
    """Convierte un ticker de yfinance en un nombre de archivo válido."""
    return pair.replace("=", "_").replace("/", "_")


def fetch_historical_data(
    pair: str,
    start_date: str,
    end_date: str | None,
    raw_path: str,
    interval: str = "1d",
) -> Path:
    """Descarga histórico OHLC para `pair` y lo guarda en `raw_path`.

    Args:
        pair: ticker en formato yfinance, ej. "EURGBP=X".
        start_date: fecha inicial "YYYY-MM-DD".
        end_date: fecha final, None para "hasta hoy".
        raw_path: carpeta donde guardar el archivo crudo.
        interval: granularidad de las velas, ej. "1d" (debe coincidir
            con data.timeframe de config/settings.yaml).

    Returns:
        Ruta al archivo CSV guardado.

    Raises:
        ValueError: si yfinance no devuelve datos para el rango/pair
            solicitado (par mal escrito, rango sin cotización, etc.).
    """
    df = yf.download(
        pair,
        start=start_date,
        end=end_date,
        interval=interval,
        progress=False,
        multi_level_index=False,
        auto_adjust=True,
    )

    if df is None or df.empty:
        raise ValueError(
            f"yfinance no devolvió datos para '{pair}' entre {start_date} y "
            f"{end_date or 'hoy'}. Verificá el ticker y el rango de fechas."
        )

    df.columns = [str(c).lower() for c in df.columns]
    df.index.name = "date"

    raw_dir = Path(raw_path)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / f"{_sanitize_filename(pair)}.csv"
    df.to_csv(out_path)

    return out_path
