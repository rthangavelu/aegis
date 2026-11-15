"""Prediction distribution drift via Population Stability Index (PSI).

Compares the first 60% of the eval dataset (baseline) against the remaining 40%
(current window) on the binary prediction column. For the mock this simulates
comparing a training-time snapshot against a recent production slice.

PSI < 0.1  → stable (pass)
PSI < 0.3  → moderate drift (warn)
PSI >= 0.3 → significant drift (fail)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _cat_psi(baseline: pd.Series, current: pd.Series) -> float:
    """PSI for a categorical/binary column."""
    cats = set(baseline.unique()) | set(current.unique())
    b_pct = {c: (baseline == c).mean() + 1e-6 for c in cats}
    c_pct = {c: (current == c).mean() + 1e-6 for c in cats}
    return float(sum((c_pct[c] - b_pct[c]) * np.log(c_pct[c] / b_pct[c]) for c in cats))


def prediction_drift(df: pd.DataFrame, pred_col: str = "prediction") -> float:
    """Return PSI between first 60% and last 40% of the prediction column."""
    if pred_col not in df.columns:
        raise KeyError(pred_col)
    n = len(df)
    split = int(n * 0.6)
    baseline = df[pred_col].iloc[:split]
    current = df[pred_col].iloc[split:]
    return _cat_psi(baseline.astype(str), current.astype(str))
