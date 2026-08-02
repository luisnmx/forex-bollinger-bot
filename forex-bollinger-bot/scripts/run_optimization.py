"""Entry point: python scripts/run_optimization.py

Corre el backtest SOLO sobre el tramo in-sample (forex_bot.backtest.validation)
probando distintas combinaciones de stop_loss / take_profit para encontrar
la que maximiza rentabilidad ajustada a riesgo, sin tocar el out-of-sample.
"""


def main():
    raise NotImplementedError("TODO: grid search de stop_loss/take_profit sobre in-sample")


if __name__ == "__main__":
    main()
