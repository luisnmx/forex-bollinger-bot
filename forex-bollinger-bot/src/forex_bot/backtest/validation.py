"""División in-sample / out-of-sample.

El in-sample se usa para optimizar parámetros (stop_loss, take_profit).
El out-of-sample NO se toca hasta tener un modelo ya optimizado, y es
donde se valida si el rendimiento se sostiene o si hubo sobreajuste.

Nota: este split simple (un único corte cronológico) es el mínimo que
usa la tesis de referencia (in_sample_ratio: 0.7 en
config/settings.yaml). Walk-forward analysis (múltiples ventanas
in/out deslizantes en vez de un solo corte) da una validación más
robusta contra sobreajuste, y es un buen siguiente paso una vez que
este split simple esté funcionando end-to-end en el pipeline.
"""

from __future__ import annotations

import pandas as pd


def split_in_out_sample(df: pd.DataFrame, in_sample_ratio: float = 0.7):
    """Divide el DataFrame cronológicamente en in-sample y out-of-sample.

    No mezcla fechas: es un único punto de corte en el tiempo, todo lo
    anterior va a in-sample y todo lo posterior a out-of-sample. El
    DataFrame se ordena por índice antes de cortar, para no depender
    de que ya venga ordenado.

    Args:
        df: DataFrame indexado por fecha (ver forex_bot.data.loader).
        in_sample_ratio: fracción de filas para in-sample, en (0, 1).
            0.7 = 70% in-sample / 30% out-of-sample (default de
            config/settings.yaml, validation.in_sample_ratio).

    Returns:
        (df_in_sample, df_out_of_sample)

    Raises:
        ValueError: si in_sample_ratio no está en (0, 1), si df está
            vacío, o si el split resultara en algún tramo vacío.
    """
    if not 0 < in_sample_ratio < 1:
        raise ValueError(
            f"in_sample_ratio debe estar entre 0 y 1 (exclusivo), recibido: {in_sample_ratio}"
        )

    if df.empty:
        raise ValueError("df está vacío, no hay nada que dividir")

    df_sorted = df.sort_index()
    split_idx = int(len(df_sorted) * in_sample_ratio)

    if split_idx == 0 or split_idx == len(df_sorted):
        raise ValueError(
            f"in_sample_ratio={in_sample_ratio} deja un tramo vacío para "
            f"{len(df_sorted)} filas. Usá un ratio menos extremo o más datos."
        )

    df_in_sample = df_sorted.iloc[:split_idx]
    df_out_of_sample = df_sorted.iloc[split_idx:]

    return df_in_sample, df_out_of_sample
