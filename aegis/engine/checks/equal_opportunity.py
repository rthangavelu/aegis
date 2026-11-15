"""Equal opportunity difference check."""

from __future__ import annotations

import pandas as pd


def equal_opportunity_difference(
    df: pd.DataFrame,
    protected_col: str,
    label_col: str = "label",
    pred_col: str = "prediction",
) -> float | None:
    if protected_col not in df.columns:
        return None
    positives = df[df[label_col] == 1]
    if positives.empty:
        return 0.0
    tpr = positives.groupby(protected_col)[pred_col].mean()
    return float(tpr.max() - tpr.min())
