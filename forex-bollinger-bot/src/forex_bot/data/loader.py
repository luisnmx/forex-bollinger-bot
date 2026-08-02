"""Carga y limpieza de datos ya descargados, listos para backtest.

Flujo: fetch.fetch_historical_data() guarda un CSV crudo en data/raw ->
clean_raw_data() lo limpia (nulos, duplicados, gaps de fin de semana) y
lo guarda en data/processed -> load_processed_data() lo carga para el
backtest.

Nota: por ahora el proyecto opera un solo par a la vez (ver
config/settings.yaml), así que cada carpeta (raw_path/processed_path)
contiene un único CSV. Si en el futuro se opera más de un par
simultáneamente, estas funciones van a necesitar un parámetro `pair`
explícito en vez de inferir el archivo por convención.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close")


def _find_single_csv(directory: str, label: str) -> Path:
    dir_path = Path(directory)
    csv_files = sorted(dir_path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No se encontró ningún CSV en {label} ('{directory}'). "
            "¿Falta correr el paso anterior del pipeline?"
        )
    if len(csv_files) > 1:
        names = ", ".join(f.name for f in csv_files)
        raise ValueError(
            f"Se esperaba un único CSV en {label} ('{directory}'), pero hay "
            f"varios: {names}. El proyecto asume un par a la vez."
        )
    return csv_files[0]


def clean_raw_data(raw_path: str, processed_path: str) -> Path:
    """Limpia el CSV crudo descargado por fetch.fetch_historical_data()
    y guarda la versión lista para backtest en `processed_path`.

    Limpieza aplicada:
        - elimina filas totalmente nulas o con nulos en open/high/low/close
        - elimina fechas duplicadas (se queda con la última)
        - elimina gaps de fin de semana (Forex no cotiza sáb/dom, pero
          algunos tickers de yfinance traen filas fantasma)
        - ordena cronológicamente

    Args:
        raw_path: carpeta con el CSV crudo (ver data.raw_path en config).
        processed_path: carpeta donde guardar el CSV limpio.

    Returns:
        Ruta al archivo CSV procesado.
    """
    raw_file = _find_single_csv(raw_path, "raw_path")
    df = pd.read_csv(raw_file, index_col=0, parse_dates=True)
    df.index.name = "date"
    df.columns = [str(c).lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"El CSV crudo '{raw_file}' no tiene las columnas: {missing}")

    df = df[list(REQUIRED_COLUMNS)]
    df = df.dropna(subset=list(REQUIRED_COLUMNS))
    df = df[~df.index.duplicated(keep="last")]
    df = df[df.index.dayofweek < 5]  # 5=sábado, 6=domingo
    df = df.sort_index()

    processed_dir = Path(processed_path)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / raw_file.name
    df.to_csv(out_path)

    return out_path


def load_processed_data(processed_path: str) -> pd.DataFrame:
    """Carga el dataset limpio para backtest.

    Args:
        processed_path: carpeta con el CSV procesado por clean_raw_data()
            (ver data.processed_path en config/settings.yaml).

    Returns:
        DataFrame con columnas: open, high, low, close, indexado por fecha.

    Raises:
        FileNotFoundError: si no hay ningún CSV en processed_path.
        ValueError: si hay más de un CSV, o si al cargado le faltan
            columnas requeridas.
    """
    processed_file = _find_single_csv(processed_path, "processed_path")
    df = pd.read_csv(processed_file, index_col=0, parse_dates=True)
    df.index.name = "date"
    df.columns = [str(c).lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"El CSV procesado '{processed_file}' no tiene las columnas: {missing}")

    return df[list(REQUIRED_COLUMNS)]
