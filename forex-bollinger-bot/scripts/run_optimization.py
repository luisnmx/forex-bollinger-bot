"""Entry point: python scripts/run_optimization.py

Grid search de stop_loss / take_profit, corriendo el backtest SOLO
sobre el tramo in-sample (forex_bot.backtest.validation), para
encontrar la combinación que maximiza profit_factor, sin tocar el
out-of-sample. El paso siguiente (fuera de este script) es validar la
combinación ganadora contra el out-of-sample para confirmar que no fue
sobreajuste.

Reusa la carga de datos y preparación de indicador/señales de
run_backtest.py (mismo pipeline: fetch/clean -> indicador), para no
duplicar esa lógica.

Correr desde la raíz del proyecto: python scripts/run_optimization.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# mismo motivo que en run_backtest.py: al correr el script directo no
# hay nada que agregue estos directorios al path.
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent / "src"))

import yaml

import run_backtest as rb
from forex_bot.backtest.engine import run_backtest
from forex_bot.backtest.metrics import profit_factor
from forex_bot.backtest.validation import split_in_out_sample
from forex_bot.indicators.bollinger import bollinger_bands
from forex_bot.strategy.bollinger_bounce import generate_signals
from forex_bot.utils.logger import get_logger

logger = get_logger(__name__)

# grid de búsqueda, como fracción del precio de entrada (0.01 = 1%)
STOP_LOSS_GRID = [0.005, 0.01, 0.015, 0.02, 0.03]
TAKE_PROFIT_GRID = [0.01, 0.02, 0.03, 0.04, 0.06]

MIN_TRADES = 10  # combinaciones con menos operaciones que esto se descartan


def _score(pf) -> float | None:
    """Puntaje a maximizar: profit_factor sobre operaciones cerradas.
    Devuelve None si no llega al mínimo de operaciones (para no
    premiar combos de stops tan ajustados que casi no operan)."""
    closed = pf.trades.closed
    if closed.count() < MIN_TRADES:
        return None
    return profit_factor(closed.winning.pnl.sum(), closed.losing.pnl.sum())


def _prepare_in_sample_data(config: dict):
    """Carga los datos, calcula el indicador y devuelve solo el tramo
    in-sample con sus señales, sin tocar el out-of-sample."""
    data_cfg = config["data"]
    df = rb._load_data(data_cfg)

    bb_cfg = config["strategy"]["bollinger"]
    bands = bollinger_bands(df["close"], period=bb_cfg["period"], std_dev=bb_cfg["std_dev"])
    df = df.join(bands)
    df_valid = df.loc[df["bb_upper"].notna()]

    in_sample_ratio = config["validation"]["in_sample_ratio"]
    df_in, _df_out = split_in_out_sample(df_valid, in_sample_ratio=in_sample_ratio)

    return df_in, generate_signals(df_in)


def optimize(config: dict) -> dict:
    """Corre el grid search sobre in-sample y devuelve la mejor
    combinación encontrada junto con la tabla completa de resultados."""
    df_in, signals_in = _prepare_in_sample_data(config)
    account_cfg = config["account"]
    freq = config["data"]["timeframe"].upper()

    all_results = []
    for sl in STOP_LOSS_GRID:
        for tp in TAKE_PROFIT_GRID:
            pf = run_backtest(
                df_in,
                signals_in,
                initial_capital=account_cfg["initial_capital"],
                stop_loss=sl,
                take_profit=tp,
                size=account_cfg["lot_size"],
                freq=freq,
            )
            all_results.append({
                "stop_loss": sl,
                "take_profit": tp,
                "profit_factor": _score(pf),
                "n_trades": pf.trades.closed.count(),
                "total_return": pf.total_return(),
            })

    valid_results = [r for r in all_results if r["profit_factor"] is not None]
    if not valid_results:
        raise RuntimeError(
            f"Ninguna combinación del grid llegó a {MIN_TRADES} operaciones en "
            "in-sample. Probá un grid con stops más anchos o más datos históricos."
        )

    best = max(valid_results, key=lambda r: r["profit_factor"])
    return {"best": best, "all_results": all_results}


def print_results(opt_results: dict) -> None:
    print("\n" + "=" * 60)
    print("OPTIMIZACIÓN stop_loss / take_profit (solo in-sample)")
    print("=" * 60)

    valid = sorted(
        (r for r in opt_results["all_results"] if r["profit_factor"] is not None),
        key=lambda r: r["profit_factor"],
        reverse=True,
    )

    print(f"{'stop_loss':>10} {'take_profit':>12} {'profit_factor':>14} {'n_trades':>9} {'return':>9}")
    for r in valid[:10]:
        print(
            f"{r['stop_loss']:>10.3f} {r['take_profit']:>12.3f} "
            f"{r['profit_factor']:>14.2f} {r['n_trades']:>9} {r['total_return'] * 100:>8.2f}%"
        )

    best = opt_results["best"]
    print("\nMejor combinación (in-sample):")
    print(f"  stop_loss={best['stop_loss']}, take_profit={best['take_profit']}")
    print(f"  profit_factor={best['profit_factor']:.2f}, n_trades={best['n_trades']}")
    print("\nOJO: esto es el resultado sobre in-sample, que es exactamente el")
    print("tramo que se usó para elegir estos parámetros -- va a verse mejor")
    print("de lo que es. El siguiente paso es correr esta misma combinación")
    print("sobre el out-of-sample (todavía sin tocar) para confirmar que no")
    print("es sobreajuste.")


def main(config_path: str = "config/settings.yaml") -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    opt_results = optimize(config)
    print_results(opt_results)
    return opt_results


if __name__ == "__main__":
    main()