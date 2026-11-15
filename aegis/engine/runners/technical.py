"""Technical runner — computes metrics from checks/ and compares to thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from aegis.engine.checks.accuracy import accuracy_floor
from aegis.engine.checks.disparate_impact import disparate_impact_ratio
from aegis.engine.checks.drift import prediction_drift
from aegis.engine.checks.equal_opportunity import equal_opportunity_difference
from aegis.engine.checks.jailbreak import (
    groundedness_score,
    jailbreak_rate,
    prompt_injection_rate,
    toxicity_rate,
)
from aegis.engine.checks.pii_leak import pii_leak_rate
from aegis.engine.checks.predictive_parity import fpr_difference
from aegis.engine.threshold import evaluate_status
from aegis.models import AISystem

_SCALAR_CHECKS = {
    "accuracy_floor": accuracy_floor,
    "jailbreak_rate": jailbreak_rate,
    "prompt_injection_rate": prompt_injection_rate,
    "toxicity_rate": toxicity_rate,
    "groundedness_score": groundedness_score,
    "pii_leak_rate": pii_leak_rate,
    "prediction_drift": prediction_drift,
}


@dataclass
class TechnicalResult:
    status: str
    metric_value: Optional[float] = None
    evidence_uri: Optional[str] = None
    message: Optional[str] = None


def _interpolate(template: str, system: AISystem) -> str:
    return template.replace("${system.eval_dataset}", system.eval_dataset or "").replace(
        "${system.id}", system.id
    )


def _load_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#")


def run(test: dict, system: AISystem, pkg_dir: Path) -> TechnicalResult:
    inputs = test.get("inputs", {})
    dataset_tmpl = inputs.get("dataset", "${system.eval_dataset}")
    dataset_rel = _interpolate(dataset_tmpl, system)
    if not dataset_rel:
        return TechnicalResult(status="error", message="No eval_dataset configured for system")

    dataset_path = pkg_dir / dataset_rel
    if not dataset_path.exists():
        return TechnicalResult(status="error", message=f"Eval dataset not found: {dataset_path}")

    df = _load_df(dataset_path)
    check = test["check"]
    metric = check["metric"]
    aggregate = check.get("aggregate", "value")

    if metric == "disparate_impact_ratio":
        attrs = inputs.get("protected_attributes", [])
        vals = [disparate_impact_ratio(df, a) for a in attrs]
        vals = [v for v in vals if v is not None]
        if not vals:
            return TechnicalResult(
                status="na", message="No applicable protected attributes in dataset"
            )
        value = min(vals) if aggregate == "min" else max(vals)

    elif metric == "equal_opportunity_difference":
        attrs = inputs.get("protected_attributes", [])
        label_col = inputs.get("label_column", "label")
        vals = [equal_opportunity_difference(df, a, label_col) for a in attrs]
        vals = [v for v in vals if v is not None]
        if not vals:
            return TechnicalResult(
                status="na", message="No applicable protected attributes in dataset"
            )
        value = max(vals) if aggregate == "max" else min(vals)

    elif metric == "fpr_difference":
        attrs = inputs.get("protected_attributes", [])
        label_col = inputs.get("label_column", "label")
        vals = [fpr_difference(df, a, label_col) for a in attrs if a in df.columns]
        vals = [v for v in vals if v is not None]
        if not vals:
            return TechnicalResult(
                status="na", message="No applicable protected attributes in dataset"
            )
        value = max(vals) if aggregate == "max" else min(vals)

    elif metric in _SCALAR_CHECKS:
        try:
            value = _SCALAR_CHECKS[metric](df)
        except KeyError as exc:
            return TechnicalResult(status="error", message=f"Missing column in dataset: {exc}")

    else:
        return TechnicalResult(status="error", message=f"Unknown metric: {metric!r}")

    status = evaluate_status(value, check)
    threshold = check.get("threshold", {})
    pass_expr = threshold.get("pass", "")
    return TechnicalResult(
        status=status,
        metric_value=round(value, 4),
        evidence_uri=str(dataset_path),
        message=f"{metric} = {value:.4f} (threshold pass {pass_expr})",
    )
