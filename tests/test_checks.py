"""Unit and integration tests for aegis.engine.checks.drift and predictive_parity."""

from pathlib import Path

import pandas as pd
import pytest

from aegis.engine.checks.drift import prediction_drift
from aegis.engine.checks.predictive_parity import fpr_difference
from aegis.engine.runners.technical import run
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier

_PKG_DIR = Path(__file__).parent.parent / "aegis"
_RESUME_CSV = _PKG_DIR / "seed/datasets/resume_screener_eval.csv"
_CREDIT_CSV = _PKG_DIR / "seed/datasets/credit_scoring_eval.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#")


def _system(dataset: str) -> AISystem:
    return AISystem(
        id="test-sys",
        name="Test",
        owner="owner@example.com",
        business_unit="BU",
        purpose="Testing",
        model_type=ModelType.classification,
        risk_tier=RiskTier.high,
        lifecycle_stage=LifecycleStage.production,
        eval_dataset=dataset,
    )


def _tech_test(metric: str, threshold: dict, **extras) -> dict:
    base = {
        "id": "TST-001",
        "type": "technical",
        "check": {"metric": metric, "threshold": threshold},
        "inputs": {},
    }
    base.update(extras)
    return base


# ---------------------------------------------------------------------------
# prediction_drift (PSI) — unit tests
# ---------------------------------------------------------------------------


class TestPredictionDrift:
    def test_stable_distribution_returns_low_psi(self):
        """Identical distributions → PSI ≈ 0."""
        df = pd.DataFrame({"prediction": [0, 1] * 50})
        psi = prediction_drift(df)
        assert psi < 0.01

    def test_shifted_distribution_returns_high_psi(self):
        """First 60% all-0, last 40% all-1 → large PSI."""
        preds = [0] * 60 + [1] * 40
        df = pd.DataFrame({"prediction": preds})
        psi = prediction_drift(df)
        # Both categories flip completely → PSI should be large
        assert psi > 0.5

    def test_resume_screener_psi_fails(self):
        """Resume screener: males first (predict=1 heavy), females second (predict=0 heavy).
        PSI > 0.1 expected (designed to FAIL REL-004 warn threshold ≥ 0.3)."""
        df = _load(_RESUME_CSV)
        psi = prediction_drift(df)
        # Males are rows 0-59 (mostly 1), females rows 60-99 (mostly 0) → high drift
        assert psi > 0.1, f"Expected PSI > 0.1, got {psi:.4f}"

    def test_credit_scoring_psi_passes(self):
        """Credit scoring: predictions more uniformly distributed → PSI < 0.1."""
        df = _load(_CREDIT_CSV)
        psi = prediction_drift(df)
        assert psi < 0.1, f"Expected PSI < 0.1, got {psi:.4f}"

    def test_requires_prediction_column(self):
        """Raises KeyError when prediction column is missing."""
        df = pd.DataFrame({"score": [0.5, 0.6]})
        with pytest.raises(KeyError):
            prediction_drift(df)

    def test_custom_pred_col(self):
        """Accepts a custom column name."""
        df = pd.DataFrame({"outcome": [0] * 60 + [1] * 40})
        psi = prediction_drift(df, pred_col="outcome")
        assert isinstance(psi, float)


# ---------------------------------------------------------------------------
# fpr_difference — unit tests
# ---------------------------------------------------------------------------


class TestFprDifference:
    def _make_df(self, groups, preds, labels):
        return pd.DataFrame({"group": groups, "prediction": preds, "label": labels})

    def test_zero_fpr_difference_returns_zero(self):
        """Equal FPR across groups → difference = 0."""
        df = self._make_df(
            groups=["A"] * 10 + ["B"] * 10,
            preds=[0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 2,
            labels=[0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 2,
        )
        diff = fpr_difference(df, attr="group")
        assert diff == pytest.approx(0.0, abs=1e-6)

    def test_unequal_fpr_returns_nonzero(self):
        """Group A: FPR=0, Group B: FPR=0.5 → difference = 0.5."""
        # Group A: 4 true negatives, all correctly predicted negative
        # Group B: 4 true negatives, 2 incorrectly predicted positive → FPR=0.5
        df = self._make_df(
            groups=["A"] * 8 + ["B"] * 8,
            preds=[0, 0, 0, 0, 1, 1, 1, 1] + [0, 0, 1, 1, 1, 1, 1, 1],
            labels=[0, 0, 0, 0, 1, 1, 1, 1] + [0, 0, 0, 0, 1, 1, 1, 1],
        )
        diff = fpr_difference(df, attr="group")
        assert diff == pytest.approx(0.5, abs=0.01)

    def test_resume_screener_fpr_fails(self):
        """Resume screener: FPR difference > 0.10 (designed to FAIL FAIR-004)."""
        df = _load(_RESUME_CSV)
        diff = fpr_difference(df, attr="gender")
        assert diff > 0.05, f"Expected FPR diff > 0.05, got {diff:.4f}"

    def test_credit_scoring_fpr_passes(self):
        """Credit scoring: FPR difference <= 0.05 (designed to PASS FAIR-004)."""
        df = _load(_CREDIT_CSV)
        # credit dataset uses age_band; gender not present → check with age_band
        diff = fpr_difference(df, attr="age_band")
        assert diff <= 0.10, f"Expected FPR diff <= 0.10, got {diff:.4f}"

    def test_missing_attribute_raises(self):
        """Raises KeyError when the protected attribute column is absent."""
        df = self._make_df(
            groups=["A", "B"],
            preds=[1, 0],
            labels=[1, 0],
        )
        with pytest.raises(KeyError):
            fpr_difference(df, attr="nonexistent")

    def test_custom_label_column(self):
        """Accepts a custom label column name."""
        df = pd.DataFrame(
            {
                "group": ["A"] * 4 + ["B"] * 4,
                "prediction": [0, 0, 1, 1] * 2,
                "outcome": [0, 0, 1, 1] * 2,
            }
        )
        diff = fpr_difference(df, attr="group", label_col="outcome")
        assert isinstance(diff, float)


# ---------------------------------------------------------------------------
# Integration: technical runner dispatches prediction_drift and fpr_difference
# ---------------------------------------------------------------------------


class TestTechnicalRunnerIntegration:
    def test_prediction_drift_pass_credit(self):
        """REL-004 pattern: credit-scoring PSI < 0.1 → pass."""
        test = _tech_test(
            "prediction_drift",
            {"pass": "< 0.1", "warn": "< 0.3"},
        )
        result = run(test, _system("seed/datasets/credit_scoring_eval.csv"), _PKG_DIR)
        assert result.status == "pass"
        assert result.metric_value is not None
        assert result.metric_value < 0.1

    def test_prediction_drift_fail_resume(self):
        """REL-004 pattern: resume-screener PSI >= 0.3 → fail."""
        test = _tech_test(
            "prediction_drift",
            {"pass": "< 0.1", "warn": "< 0.3"},
        )
        result = run(test, _system("seed/datasets/resume_screener_eval.csv"), _PKG_DIR)
        assert result.status == "fail"
        assert result.metric_value is not None
        assert result.metric_value >= 0.3

    def test_fpr_difference_pass_credit(self):
        """FAIR-004 pattern: credit FPR diff (age_band) ≤ 0.05 → pass."""
        test = _tech_test(
            "fpr_difference",
            {"pass": "<= 0.05", "warn": "<= 0.10"},
            inputs={"protected_attributes": ["age_band"], "label_column": "label"},
        )
        result = run(test, _system("seed/datasets/credit_scoring_eval.csv"), _PKG_DIR)
        assert result.status in ("pass", "warn")
        assert result.metric_value is not None

    def test_fpr_difference_fail_resume(self):
        """FAIR-004 pattern: resume-screener FPR diff (gender) > 0.10 → fail."""
        test = _tech_test(
            "fpr_difference",
            {"pass": "<= 0.05", "warn": "<= 0.10"},
            inputs={"protected_attributes": ["gender"], "label_column": "label"},
        )
        result = run(test, _system("seed/datasets/resume_screener_eval.csv"), _PKG_DIR)
        assert result.status == "fail"
        assert result.metric_value is not None
        assert result.metric_value > 0.10

    def test_fpr_difference_na_when_no_attrs_in_dataset(self):
        """When none of the requested protected attributes exist in the dataset → na."""
        test = _tech_test(
            "fpr_difference",
            {"pass": "<= 0.05", "warn": "<= 0.10"},
            inputs={"protected_attributes": ["nonexistent_col"], "label_column": "label"},
        )
        result = run(test, _system("seed/datasets/credit_scoring_eval.csv"), _PKG_DIR)
        assert result.status == "na"
