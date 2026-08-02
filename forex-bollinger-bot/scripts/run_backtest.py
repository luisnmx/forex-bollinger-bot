"""Entry point: python scripts/run_backtest.py

Pipeline:
    1. Cargar config/settings.yaml
    2. Cargar datos procesados (forex_bot.data.loader)
    3. Calcular indicador (forex_bot.indicators.bollinger)
    4. Generar señales (forex_bot.strategy.bollinger_bounce)
    5. Correr backtest (forex_bot.backtest.engine)
    6. Calcular métricas (forex_bot.backtest.metrics)
    7. Imprimir/guardar resultados
"""

import yaml


def main():
    with open("config/settings.yaml") as f:
        config = yaml.safe_load(f)

    print(f"Config cargada para: {config['data']['pair']}")
    raise NotImplementedError("TODO: conectar el pipeline completo")


if __name__ == "__main__":
    main()
