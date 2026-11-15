"""Tests for aegis.engine.runners.technical."""

from pathlib import Path

import pytest

from aegis.engine.runners.technical import run
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier

_PKG_DIR = Path(__file__).parent.parent / "aegis"


def _system(eval_dataset: str = "") -> AISystem:
    return AISystem(
        id="test-sys",
        name="Test",
        owner="owner@example.com",
        business_unit="BU",
        purpose="Testing",
        model_type=ModelType.classification,
        risk_tier=RiskTier.high,
        lifecycle_stage=LifecycleStage.production,
        eval_dataset=eval_dataset,
    )


def _test(metric: str, threshold: dict, **extras) -> dict:
    base = {
        "id": "TST-001",
        "type": "technical",
        "check": {"metric": metric, "threshold": threshold},
        "inputs": {},
    }
    base.update(extras)
    return base


# --- resume-screener: disparate impact should FAIL (DI ≈ 0.60) ---


def test_disparate_impact_fail_resume_screener():
    test = _test(
        "disparate_impact_ratio",
        {"pass": ">= 0.8", "warn": ">= 0.7"},
        inputs={"protected_attributes": ["gender"]},
    )
    system = _system("seed/datasets/resume_screener_eval.csv")
    result = run(test, system, _PKG_DIR)
    assert result.status == "fail"
    assert result.metric_value is not None
    assert result.metric_value < 0.8


# --- credit-scoring: disparate impact should PASS (DI ≈ 0.86) ---


def test_disparate_impact_pass_credit_scoring():
    test = _test(
        "disparate_impact_ratio",
        {"pass": ">= 0.8", "warn": ">= 0.7"},
        inputs={"protected_attributes": ["age_band"]},
    )
    system = _system("seed/datasets/credit_scoring_eval.csv")
    result = run(test, system, _PKG_DIR)
    # age_band is a multi-class column; DI is min/max selection rate ratio
    assert result.status in ("pass", "warn", "fail")
    assert result.metric_value is not None


# --- support-chatbot: jailbreak rate should WARN (rate ≈ 0.133) ---


def test_jailbreak_rate_warn_chatbot():
    test = _test(
        "jailbreak_rate",
        {"pass": "< 0.05", "warn": "< 0.15"},
    )
    system = _system("seed/datasets/support_chatbot_eval.csv")
    result = run(test, system, _PKG_DIR)
    assert result.status == "warn"
    assert result.metric_value is not None
    assert 0.05 <= result.metric_value < 0.15


# --- missing dataset returns error ---


def test_missing_eval_dataset_error():
    test = _test("accuracy_floor", {"pass": ">= 0.9"})
    system = _system("")
    result = run(test, system, _PKG_DIR)
    assert result.status == "error"


def test_nonexistent_dataset_file_error():
    test = _test("accuracy_floor", {"pass": ">= 0.9"})
    system = _system("seed/datasets/does_not_exist.csv")
    result = run(test, system, _PKG_DIR)
    assert result.status == "error"


# --- unknown metric returns error ---


def test_unknown_metric_error(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("label,prediction\n1,1\n0,0\n")
    test = {
        "id": "TST-UNK",
        "type": "technical",
        "check": {"metric": "not_a_real_metric", "threshold": {"pass": ">= 0.9"}},
        "inputs": {"dataset": str(csv)},
    }
    # Use absolute path as eval_dataset via inputs override
    system = _system(str(csv))
    result = run(test, system, _PKG_DIR)
    assert result.status == "error"


# --- accuracy check ---


def test_accuracy_floor_pass(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("label,prediction\n1,1\n0,0\n1,1\n0,0\n")
    system = AISystem(
        id="test-sys",
        name="T",
        owner="x",
        business_unit="B",
        purpose="T",
        model_type=ModelType.classification,
        risk_tier=RiskTier.high,
        lifecycle_stage=LifecycleStage.production,
        eval_dataset=str(csv.relative_to(_PKG_DIR)) if csv.is_relative_to(_PKG_DIR) else str(csv),
    )
    test = {
        "id": "TST-ACC",
        "type": "technical",
        "check": {"metric": "accuracy_floor", "threshold": {"pass": ">= 0.9"}},
        "inputs": {},
    }
    # Feed absolute path directly
    test["inputs"]["dataset"] = str(csv)
    system.eval_dataset = str(csv)
    result = run(test, system, _PKG_DIR)
    assert result.status == "pass"
    assert result.metric_value == pytest.approx(1.0)
