"""Tests del motor de backtest y del split in-sample/out-of-sample.

TODO: verificar que split_in_out_sample() no mezcla fechas y que
run_backtest() produce un objeto de resultados coherente.
"""

import pandas as pd
import pytest

from forex_bot.backtest.validation import split_in_out_sample


def test_split_in_out_sample_not_implemented_yet():
    df = pd.DataFrame({"close": range(100)})
    with pytest.raises(NotImplementedError):
        split_in_out_sample(df, in_sample_ratio=0.7)
