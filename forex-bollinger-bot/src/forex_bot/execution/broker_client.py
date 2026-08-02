"""Wrapper sobre la API del bróker (OANDA, MT5, etc.).

TODO: implementar cuando se llegue a la fase de demo/forwardtest.
No se necesita para el backtest.
"""


class BrokerClient:
    def __init__(self, api_key: str, account_id: str, environment: str = "demo"):
        raise NotImplementedError("TODO: inicializar conexión con la API del bróker")

    def place_order(self, pair: str, side: str, units: int):
        raise NotImplementedError("TODO: enviar orden de mercado")

    def get_open_positions(self):
        raise NotImplementedError("TODO: consultar posiciones abiertas")
