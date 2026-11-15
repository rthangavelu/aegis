"""PII leak rate check (mock)."""

from __future__ import annotations

import pandas as pd


def pii_leak_rate(df: pd.DataFrame) -> float:
    return float(df["pii_in_response"].mean())
