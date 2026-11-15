"""Disparate impact ratio check — four-fifths rule."""

from __future__ import annotations

import pandas as pd


def disparate_impact_ratio(
    df: pd.DataFrame,
    protected_col: str,
    outcome_col: str = "prediction",
) -> float | None:
    if protected_col not in df.columns or outcome_col not in df.columns:
        return None
    rates = df.groupby(protected_col)[outcome_col].mean()
    max_rate = rates.max()
    if max_rate == 0:
        return 1.0
    return float(rates.min() / max_rate)
