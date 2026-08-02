"""Entry point: python scripts/run_backtest.py

Pipeline:
    1. Cargar config/settings.yaml
    2. Cargar datos procesados (forex_bot.data.loader); si no existen
       todavía, se descargan y limpian primero (fetch + clean).
    3. Calcular indicador (forex_bot.indicators.bollinger)
    4. Generar señales (forex_bot.strategy.bollinger_bounce)
    5. Correr backtest (forex_bot.backtest.engine) — sin stop_loss ni
       take_profit: esos se definen en la fase de optimización
       (scripts/run_optimization.py), no acá. Este es el "backtest
       simple de sanidad" sobre todo el histórico.
    6. Calcular métricas (forex_bot.backtest.metrics)
    7. Imprimir resultados

Correr desde la raíz del proyecto: python scripts/run_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# pytest.ini resuelve esto vía pythonpath=src, pero al correr el script
# directo (python3 scripts/run_backtest.py) no hay nada que agregue
# src/ al path — lo hacemos acá para que funcione sin pasos extra.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml

from forex_bot.backtest.engine import run_backtest
from forex_bot.backtest.metrics import profit_factor, recovery_factor, sharpe_ratio, value_at_risk
from forex_bot.data.fetch import fetch_historical_data
from forex_bot.data.loader import clean_raw_data, load_processed_data
from forex_bot.indicators.bollinger import bollinger_bands
from forex_bot.strategy.bollinger_bounce import generate_signals
from forex_bot.utils.logger import get_logger

logger = get_logger(__name__)

TRADING_DAYS_PER_YEAR = 252


def _load_data(data_cfg: dict):
    """Carga los datos procesados; si no existen todavía, los descarga
    y limpia primero."""
    try:
        return load_processed_data(data_cfg["processed_path"])
    except FileNotFoundError:
        logger.info("No hay datos procesados todavía, descargando con yfinance...")
        fetch_historical_data(
            pair=data_cfg["pair"],
            start_date=data_cfg["start_date"],
            end_date=data_cfg["end_date"],
            raw_path=data_cfg["raw_path"],
            interval=data_cfg["timeframe"],
        )
        clean_raw_data(raw_path=data_cfg["raw_path"], processed_path=data_cfg["processed_path"])
        return load_processed_data(data_cfg["processed_path"])


def run_pipeline(config: dict) -> dict:
    """Corre el pipeline completo a partir de un dict de config ya
    cargado (ver config/settings.yaml) y devuelve un resumen de
    resultados. Separado de main() para poder testearlo sin depender
    de un archivo de config en disco."""
    data_cfg = config["data"]
    pair = data_cfg["pair"]
    logger.info(f"Config cargada para: {pair}")

    df = _load_data(data_cfg)
    logger.info(f"Datos cargados: {len(df)} filas ({df.index.min().date()} a {df.index.max().date()})")

    bb_cfg = config["strategy"]["bollinger"]
    bands = bollinger_bands(df["close"], period=bb_cfg["period"], std_dev=bb_cfg["std_dev"])
    df = df.join(bands)

    # las primeras `period - 1` filas no tienen banda calculada (NaN);
    # se descartan antes del backtest en vez de dejar que las señales
    # las ignoren silenciosamente
    valid = df["bb_upper"].notna()
    df_valid = df.loc[valid]
    signals_valid = generate_signals(df_valid)

    account_cfg = config["account"]
    pf = run_backtest(
        df_valid,
        signals_valid,
        initial_capital=account_cfg["initial_capital"],
        size=account_cfg["lot_size"],
        freq=data_cfg["timeframe"].upper(),  # "1d" -> "1D"
    )

    # unidades consistentes: recovery_factor compara retorno neto (%)
    # contra max drawdown (%), no beneficio en $ contra drawdown en %
    net_return = pf.total_return()
    max_dd = abs(pf.max_drawdown())
    # solo operaciones CERRADAS: incluir el PnL en papel de una
    # operación todavía abierta sesgaría profit_factor (esa pérdida/
    # ganancia no realizada puede revertirse antes de cerrarse)
    gross_profit = pf.trades.closed.winning.pnl.sum()
    gross_loss = pf.trades.closed.losing.pnl.sum()
    returns = pf.returns()

    results = {
        "pair": pair,
        "portfolio": pf,
        "net_return": net_return,
        "max_drawdown": max_dd,
        "profit_factor": profit_factor(gross_profit, gross_loss),
        "recovery_factor": recovery_factor(net_return, max_dd) if max_dd > 0 else None,
        "sharpe_ratio": None,
        "value_at_risk_95": None,
    }

    if len(returns) >= 2 and returns.std() > 0:
        results["sharpe_ratio"] = sharpe_ratio(returns, annualize_periods=TRADING_DAYS_PER_YEAR)
        sigma_annual = returns.std() * (TRADING_DAYS_PER_YEAR ** 0.5)
        results["value_at_risk_95"] = value_at_risk(
            capital=account_cfg["initial_capital"], sigma=sigma_annual, confidence=0.95
        )

    return results


def print_results(results: dict) -> None:
    print("\n" + "=" * 60)
    print(f"BACKTEST — {results['pair']}")
    print("=" * 60)
    print(results["portfolio"].stats())

    print("\n--- Métricas de robustez (umbrales de referencia, IV.3.3) ---")
    print("(recovery/profit factor y VaR calculados con forex_bot.backtest.metrics;")
    print(" el Sharpe puede diferir levemente del 'Sharpe Ratio' de vectorbt de arriba")
    print(" por convenciones distintas de anualización — ambos son válidos)")

    rf = results["recovery_factor"]
    if rf is not None:
        print(f"Recovery factor: {rf:.2f}  (> 6 esperado){'  ok' if rf > 6 else '  x'}")
    else:
        print("Recovery factor: sin drawdown, no se puede calcular")

    pfac = results["profit_factor"]
    print(f"Profit factor:   {pfac:.2f}  (> 2 esperado){'  ok' if pfac > 2 else '  x'}")

    sr = results["sharpe_ratio"]
    if sr is not None:
        print(f"Sharpe ratio:    {sr:.2f}  (> 2 esperado){'  ok' if sr > 2 else '  x'}")
    else:
        print("Sharpe ratio: retornos insuficientes o sin variación")

    var = results["value_at_risk_95"]
    if var is not None:
        print(f"VaR mensual (95%): {var:.2f}")


def main(config_path: str = "config/settings.yaml") -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    results = run_pipeline(config)
    print_results(results)
    return results


if __name__ == "__main__":
    main()
