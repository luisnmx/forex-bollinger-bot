"""Entry point: python scripts/run_live.py

Solo usar después de validar out-of-sample y confirmar métricas de
robustez. Corre el bot contra la cuenta demo/real definida en .env.
"""

from forex_bot.execution.live_runner import run_live


def main():
    raise NotImplementedError("TODO: cargar config y credenciales, llamar a run_live()")


if __name__ == "__main__":
    main()
