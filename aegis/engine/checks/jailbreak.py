"""Jailbreak rate and prompt injection rate checks (mock)."""

from __future__ import annotations

import pandas as pd


def jailbreak_rate(df: pd.DataFrame) -> float:
    attempts = df[df["jailbreak_attempt"] == 1]
    if attempts.empty:
        return 0.0
    return float(attempts["jailbreak_success"].mean())


def prompt_injection_rate(df: pd.DataFrame) -> float:
    # Mock: use same jailbreak_success column as proxy for prompt injection.
    return jailbreak_rate(df)


def toxicity_rate(df: pd.DataFrame) -> float:
    return float(df["toxicity_score"].mean())


def groundedness_score(df: pd.DataFrame) -> float:
    return float(df["groundedness_score"].mean())
