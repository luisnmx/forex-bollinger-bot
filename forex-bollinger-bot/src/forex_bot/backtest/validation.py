"""División in-sample / out-of-sample.

El in-sample se usa para optimizar parámetros (stop_loss, take_profit).
El out-of-sample NO se toca hasta tener un modelo ya optimizado, y es
donde se valida si el rendimiento se sostiene o si hubo sobreajuste.
"""

import pandas as pd


def split_in_out_sample(df: pd.DataFrame, in_sample_ratio: float = 0.7):
    """Divide el DataFrame cronológicamente.

    Returns:
        (df_in_sample, df_out_of_sample)
    """
    raise NotImplementedError("TODO: split cronológico simple, sin mezclar fechas")
