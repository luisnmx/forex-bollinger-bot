# forex-bollinger-bot

Modelo de trading algorítmico Bollinger Bounce para EUR/GBP (marco diario),
construido siguiendo esta ruta:

1. Definir el modelo y sus reglas (`src/forex_bot/strategy/bollinger_bounce.py`)
2. Obtener datos históricos (`src/forex_bot/data/fetch.py`)
3. Codificar indicador + reglas (`src/forex_bot/indicators/`, `strategy/`)
4. Backtest simple de sanidad (`scripts/run_backtest.py`)
5. Split in-sample / out-of-sample (`src/forex_bot/backtest/validation.py`)
6. Optimizar stop_loss / take_profit solo en in-sample (`scripts/run_optimization.py`)
7. Validar en out-of-sample
8. Calcular ratios de robustez (`src/forex_bot/backtest/metrics.py`)
9. Demo / forwardtest antes de capital real (`scripts/run_live.py`)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # rellenar cuando se llegue a la fase de demo
```

## Uso

```bash
python scripts/run_backtest.py
python scripts/run_optimization.py
python scripts/run_live.py     # solo tras validar out-of-sample
```

## Estructura

Ver `src/forex_bot/` para la lógica y `scripts/` para los puntos de entrada
ejecutables. `config/settings.yaml` centraliza par, timeframe y parámetros.
