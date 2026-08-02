"""Entry point: python scripts/run_prop_firm_check.py

Corre el backtest sobre todo el histórico disponible y evalúa si el
resultado habría pasado un challenge de cuenta de fondeo de 2 fases
(ver forex_bot.backtest.prop_firm para las reglas y los supuestos).

Fase 1 / Fase 2 se simulan sobre el mismo corte cronológico que usa
validation.split_in_out_sample() (validation.in_sample_ratio de
config/settings.yaml): el tramo "in-sample" hace de candidato a
Fase 1, y el "out-of-sample" de candidato a Fase 2. No son datos
elegidos al azar, son los mismos tramos que ya usás para optimizar y
validar el modelo — la idea es responder "si hubiera operado así
durante este período, ¿pasaba el challenge?", no simular un challenge
real con fechas de inicio arbitrarias.

Reglas por defecto: las de config/settings.yaml, sección prop_firm.
Podés pasar stop_loss/take_profit (ej. los que salieron de
run_optimization.py) para evaluar el modelo CON esos stops en vez del
backtest sin stops.

Correr desde la raíz del proyecto: python scripts/run_prop_firm_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent / "src"))

import yaml

import run_backtest as rb
from forex_bot.backtest.engine import run_backtest
from forex_bot.backtest.prop_firm import daily_pnl_from_portfolio, evaluate_two_phase_challenge
from forex_bot.backtest.validation import split_in_out_sample
from forex_bot.indicators.bollinger import bollinger_bands
from forex_bot.strategy.bollinger_bounce import generate_signals
from forex_bot.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PROP_FIRM_RULES = {
    "profit_target_pct": 0.06,
    "max_daily_loss_pct": 0.03,
    "max_total_drawdown_pct": 0.06,
    "max_daily_profit_share_pct": 0.35,
    "min_trading_days": 1,
}


def check_prop_firm_challenge(
    config: dict,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> dict:
    """Corre el pipeline completo y evalúa el challenge de 2 fases."""
    data_cfg = config["data"]
    account_cfg = config["account"]
    rules = {**DEFAULT_PROP_FIRM_RULES, **config.get("prop_firm", {})}

    df = rb._load_data(data_cfg)
    bb_cfg = config["strategy"]["bollinger"]
    bands = bollinger_bands(df["close"], period=bb_cfg["period"], std_dev=bb_cfg["std_dev"])
    df = df.join(bands)
    df_valid = df.loc[df["bb_upper"].notna()]

    in_sample_ratio = config["validation"]["in_sample_ratio"]
    df_phase1, df_phase2 = split_in_out_sample(df_valid, in_sample_ratio=in_sample_ratio)

    freq = data_cfg["timeframe"].upper()
    initial_capital = account_cfg["initial_capital"]
    lot_size = account_cfg["lot_size"]

    pf1 = run_backtest(
        df_phase1, generate_signals(df_phase1), initial_capital=initial_capital,
        stop_loss=stop_loss, take_profit=take_profit, size=lot_size, freq=freq,
    )
    pf2 = run_backtest(
        df_phase2, generate_signals(df_phase2), initial_capital=initial_capital,
        stop_loss=stop_loss, take_profit=take_profit, size=lot_size, freq=freq,
    )

    daily_pnl_phase1 = daily_pnl_from_portfolio(pf1, initial_capital)
    daily_pnl_phase2 = daily_pnl_from_portfolio(pf2, initial_capital)

    challenge_result = evaluate_two_phase_challenge(
        daily_pnl_phase1, daily_pnl_phase2, initial_capital, **rules
    )
    challenge_result["rules"] = rules
    challenge_result["stop_loss"] = stop_loss
    challenge_result["take_profit"] = take_profit
    return challenge_result


def print_results(result: dict) -> None:
    print("\n" + "=" * 60)
    print("CHALLENGE DE CUENTA DE FONDEO (2 fases)")
    print("=" * 60)
    r = result["rules"]
    print(
        f"Reglas: objetivo {r['profit_target_pct']*100:.0f}% / fase, "
        f"pérdida diaria máx {r['max_daily_loss_pct']*100:.0f}%, "
        f"pérdida total máx {r['max_total_drawdown_pct']*100:.0f}%, "
        f"consistencia {r['max_daily_profit_share_pct']*100:.0f}%"
    )
    if result["stop_loss"] or result["take_profit"]:
        print(f"stop_loss={result['stop_loss']}, take_profit={result['take_profit']}")
    else:
        print("Sin stop_loss ni take_profit (backtest simple)")

    for phase_num in (1, 2):
        phase = result.get(f"phase{phase_num}")
        if phase is None:
            print(f"\nFase {phase_num}: no se llegó a evaluar")
            continue
        status = "PASÓ" if phase["passed"] else "NO PASÓ"
        print(f"\nFase {phase_num}: {status}  (motivo: {phase['reason']})")
        print(f"  Fecha del evento: {phase['date']}")
        print(f"  Retorno neto: {phase['net_profit_pct']*100:.2f}%")
        print(f"  Días operados: {phase['trading_days']}")

    print(f"\nResultado final: {'PASARÍA el challenge' if result['passed'] else 'NO pasaría el challenge'}")
    if not result["passed"] and result["failed_phase"]:
        print(f"(se cae en la Fase {result['failed_phase']})")

    print(
        "\nRecordatorio: esto usa drawdown diario/total aproximados sobre velas"
        "\ndiarias (no intradía) y drawdown total estático, no trailing."
        "\nVer el docstring de forex_bot.backtest.prop_firm antes de confiar"
        "\nen este resultado para una firm real -- revisá sus reglas exactas."
    )


def main(config_path: str = "config/settings.yaml", stop_loss: float | None = None, take_profit: float | None = None) -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    result = check_prop_firm_challenge(config, stop_loss=stop_loss, take_profit=take_profit)
    print_results(result)
    return result


if __name__ == "__main__":
    main()
