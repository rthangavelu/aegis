"""False Positive Rate parity check.

Measures whether the model imposes a disproportionate false positive burden on
any protected group. FPR = FP / (FP + TN) — among individuals who should NOT
be selected, what fraction are incorrectly selected by the model?

FPR difference <= 0.05 → pass
FPR difference <= 0.10 → warn
FPR difference  > 0.10 → fail
"""

from __future__ import annotations

import pandas as pd
from fairlearn.metrics import MetricFrame, false_positive_rate


def fpr_difference(df: pd.DataFrame, attr: str, label_col: str = "label") -> float:
    """Return max FPR difference across groups of protected attribute `attr`."""
    if attr not in df.columns:
        raise KeyError(attr)
    if label_col not in df.columns:
        raise KeyError(label_col)

    mf = MetricFrame(
        metrics=false_positive_rate,
        y_true=df[label_col],
        y_pred=df["prediction"],
        sensitive_features=df[attr],
    )
    return float(mf.difference(method="between_groups"))
