"""Tests de descarga (fetch.py) y limpieza/carga (loader.py) de datos.

fetch_historical_data() se testea con yfinance.download mockeado, para
no depender de red ni de que el mercado esté abierto.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from forex_bot.data.fetch import fetch_historical_data
from forex_bot.data.loader import clean_raw_data, load_processed_data


# ---------------------------------------------------------------------------
# fetch_historical_data
# ---------------------------------------------------------------------------

def _fake_yf_download(*args, **kwargs):
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame({
        "Open": [1.10, 1.11, 1.12, 1.11, 1.13],
        "High": [1.12, 1.12, 1.13, 1.12, 1.14],
        "Low":  [1.09, 1.10, 1.11, 1.10, 1.12],
        "Close": [1.11, 1.12, 1.11, 1.12, 1.13],
        "Volume": [0, 0, 0, 0, 0],
    }, index=idx)


def test_fetch_historical_data_saves_csv(tmp_path):
    with patch("forex_bot.data.fetch.yf.download", side_effect=_fake_yf_download):
        out_path = fetch_historical_data(
            pair="EURGBP=X", start_date="2024-01-01", end_date=None,
            raw_path=str(tmp_path),
        )
    assert out_path.exists()
    assert out_path.name == "EURGBP_X.csv"

    df = pd.read_csv(out_path, index_col=0)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 5


def test_fetch_historical_data_empty_response_raises(tmp_path):
    with patch("forex_bot.data.fetch.yf.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="no devolvió datos"):
            fetch_historical_data(
                pair="INVALID=X", start_date="2024-01-01", end_date=None,
                raw_path=str(tmp_path),
            )


# ---------------------------------------------------------------------------
# clean_raw_data / load_processed_data
# ---------------------------------------------------------------------------

def _write_raw_csv(raw_dir, filename="EURGBP_X.csv"):
    # incluye: un sábado y domingo (deben eliminarse), un nulo (debe
    # eliminarse) y una fecha duplicada (debe quedarse con la última)
    idx = pd.to_datetime([
        "2024-01-01",  # lunes
        "2024-01-02",  # martes
        "2024-01-02",  # duplicado martes (última gana)
        "2024-01-06",  # sábado -> se elimina
        "2024-01-07",  # domingo -> se elimina
        "2024-01-08",  # lunes, con nulo -> se elimina
        "2024-01-09",  # martes
    ])
    df = pd.DataFrame({
        "open":  [1.10, 1.11, 1.115, 1.20, 1.20, 1.12, 1.13],
        "high":  [1.12, 1.12, 1.125, 1.21, 1.21, 1.14, 1.15],
        "low":   [1.09, 1.10, 1.105, 1.19, 1.19, None, 1.12],
        "close": [1.11, 1.115, 1.12, 1.20, 1.20, 1.13, 1.14],
    }, index=idx)
    df.index.name = "date"
    path = raw_dir / filename
    df.to_csv(path)
    return path


def test_clean_raw_data_removes_weekends_duplicates_and_nulls(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    _write_raw_csv(raw_dir)

    out_path = clean_raw_data(str(raw_dir), str(processed_dir))
    df = pd.read_csv(out_path, index_col=0, parse_dates=True)

    # quedan: 2024-01-01, 2024-01-02 (última versión), 2024-01-09
    assert len(df) == 3
    assert df.index.dayofweek.max() < 5
    assert not df.index.duplicated().any()
    assert df.loc["2024-01-02", "close"] == 1.12  # se quedó con la última
    assert not df.isna().any().any()


def test_clean_raw_data_sorts_chronologically(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    _write_raw_csv(raw_dir)

    out_path = clean_raw_data(str(raw_dir), str(processed_dir))
    df = pd.read_csv(out_path, index_col=0, parse_dates=True)
    assert df.index.is_monotonic_increasing


def test_load_processed_data_returns_ohlc(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    pd.DataFrame({
        "open": [1.1, 1.2, 1.3], "high": [1.2, 1.3, 1.4],
        "low": [1.0, 1.1, 1.2], "close": [1.15, 1.25, 1.35],
    }, index=idx).to_csv(processed_dir / "EURGBP_X.csv")

    df = load_processed_data(str(processed_dir))
    assert list(df.columns) == ["open", "high", "low", "close"]
    assert len(df) == 3


def test_load_processed_data_no_file_raises(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_processed_data(str(processed_dir))


def test_load_processed_data_multiple_files_raises(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    df = pd.DataFrame({"open": [1, 1], "high": [1, 1], "low": [1, 1], "close": [1, 1]}, index=idx)
    df.to_csv(processed_dir / "a.csv")
    df.to_csv(processed_dir / "b.csv")
    with pytest.raises(ValueError, match="único CSV"):
        load_processed_data(str(processed_dir))
