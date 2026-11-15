"""Accuracy floor check."""

from __future__ import annotations

import pandas as pd


def accuracy_floor(
    df: pd.DataFrame,
    pred_col: str = "prediction",
    label_col: str = "label",
) -> float:
    return float((df[pred_col] == df[label_col]).mean())
