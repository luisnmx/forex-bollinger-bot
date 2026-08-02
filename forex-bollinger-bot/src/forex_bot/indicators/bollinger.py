"""Cálculo de Bandas de Bollinger.

Nota: no usamos pandas-ta a propósito. El paquete cambió de mantenedor
en circunstancias sospechosas (historial borrado en PyPI, señales de
posible ataque a la cadena de suministro), y el cálculo de Bollinger
es lo bastante simple como para no necesitar la dependencia.
"""

import pandas as pd


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Calcula banda superior, media móvil y banda inferior.

    Args:
        close: serie de precios de cierre.
        period: número de periodos para la media móvil (20 por defecto).
        std_dev: número de desviaciones estándar para las bandas (2 por defecto).

    Returns:
        DataFrame con columnas: bb_mid, bb_upper, bb_lower.
    """
    bb_mid = close.rolling(window=period).mean()
    bb_std = close.rolling(window=period).std()

    bb_upper = bb_mid + std_dev * bb_std
    bb_lower = bb_mid - std_dev * bb_std

    return pd.DataFrame({
        "bb_mid": bb_mid,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
    })
