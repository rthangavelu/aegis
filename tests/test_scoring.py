"""Unit tests for aegis.scoring.engine — one test per INTENT.md section 8 rule."""

import pytest

from aegis.models import RAGStatus, TestStatus
from aegis.scoring.engine import (
    aegis_index,
    load_config,
    maturity_level,
    pillar_score,
    rag_status,
    severity_weight,
    status_points,
)

CFG = load_config()


# --- Rule 1: Status points ---


def test_pass_scores_one():
    assert status_points(TestStatus.pass_, CFG) == 1.0


def test_warn_scores_half():
    assert status_points(TestStatus.warn, CFG) == 0.5


def test_fail_scores_zero():
    assert status_points(TestStatus.fail, CFG) == 0.0


def test_error_scores_zero():
    assert status_points(TestStatus.error, CFG) == 0.0


# --- Rule 2: Severity weights ---


def test_critical_weight_four():
    assert severity_weight("critical", CFG) == 4


def test_high_weight_three():
    assert severity_weight("high", CFG) == 3


def test_medium_weight_two():
    assert severity_weight("medium", CFG) == 2


def test_low_weight_one():
    assert severity_weight("low", CFG) == 1


# --- Rule 4: Pillar score formula ---


def _pair(status: TestStatus, severity: str) -> tuple:
    class R:
        pass

    r = R()
    r.status = status
    return (r, {"severity": severity})


def test_pillar_all_pass():
    pairs = [_pair(TestStatus.pass_, "high"), _pair(TestStatus.pass_, "medium")]
    assert pillar_score(pairs, CFG) == pytest.approx(100.0)


def test_pillar_all_fail():
    pairs = [_pair(TestStatus.fail, "high"), _pair(TestStatus.fail, "low")]
    assert pillar_score(pairs, CFG) == pytest.approx(0.0)


def test_pillar_mixed():
    # one high pass (3×1=3), one high fail (3×0=0) → 100×3/6 = 50
    pairs = [_pair(TestStatus.pass_, "high"), _pair(TestStatus.fail, "high")]
    assert pillar_score(pairs, CFG) == pytest.approx(50.0)


def test_pillar_warn_counts_half():
    # one medium warn (2×0.5=1), one medium pass (2×1=2) → 100×3/4 = 75
    pairs = [_pair(TestStatus.warn, "medium"), _pair(TestStatus.pass_, "medium")]
    assert pillar_score(pairs, CFG) == pytest.approx(75.0)


def test_pillar_na_excluded():
    # na and pending excluded — only high pass counts → 100
    pairs = [
        _pair(TestStatus.pass_, "high"),
        _pair(TestStatus.na, "critical"),
        _pair(TestStatus.pending, "critical"),
    ]
    assert pillar_score(pairs, CFG) == pytest.approx(100.0)


def test_pillar_all_na_returns_zero():
    pairs = [_pair(TestStatus.na, "high"), _pair(TestStatus.pending, "low")]
    assert pillar_score(pairs, CFG) == pytest.approx(0.0)


def test_pillar_na_excluded_from_denominator():
    # na contributes neither points nor weight
    pairs = [_pair(TestStatus.pass_, "low"), _pair(TestStatus.na, "critical")]
    assert pillar_score(pairs, CFG) == pytest.approx(100.0)


def test_pillar_severity_weights_matter():
    # critical fail (4×0=0) + low pass (1×1=1) → 100×1/5 = 20
    pairs = [_pair(TestStatus.fail, "critical"), _pair(TestStatus.pass_, "low")]
    assert pillar_score(pairs, CFG) == pytest.approx(20.0)


# --- Rule 5: Maturity bands ---


def test_maturity_0_to_20_is_1():
    assert maturity_level(0.0, CFG) == 1
    assert maturity_level(20.0, CFG) == 1


def test_maturity_21_to_40_is_2():
    assert maturity_level(21.0, CFG) == 2
    assert maturity_level(40.0, CFG) == 2


def test_maturity_41_to_60_is_3():
    assert maturity_level(50.0, CFG) == 3


def test_maturity_61_to_80_is_4():
    assert maturity_level(70.0, CFG) == 4
    assert maturity_level(80.0, CFG) == 4


def test_maturity_81_to_100_is_5():
    assert maturity_level(81.0, CFG) == 5
    assert maturity_level(100.0, CFG) == 5


# --- Rule 8: RAG status ---


def test_rag_green_at_80():
    assert rag_status(80.0, False, CFG) == RAGStatus.green


def test_rag_green_above_80():
    assert rag_status(95.0, False, CFG) == RAGStatus.green


def test_rag_amber_at_60():
    assert rag_status(60.0, False, CFG) == RAGStatus.amber


def test_rag_amber_at_79():
    assert rag_status(79.9, False, CFG) == RAGStatus.amber


def test_rag_red_below_60():
    assert rag_status(59.9, False, CFG) == RAGStatus.red


def test_rag_red_at_zero():
    assert rag_status(0.0, False, CFG) == RAGStatus.red


# --- Rule 7: Critical cap ---


def test_critical_cap_forces_red_even_at_100():
    assert rag_status(100.0, True, CFG) == RAGStatus.red


def test_critical_cap_forces_red_even_at_80():
    assert rag_status(80.0, True, CFG) == RAGStatus.red


def test_no_critical_fail_no_cap():
    assert rag_status(80.0, False, CFG) == RAGStatus.green


# --- Rule 6: Aegis Index ---


def test_aegis_index_equal_weights():
    # two pillars with equal weights → simple average
    scores = [("Fairness", 100.0), ("Privacy & Data", 60.0)]
    weights = {"Fairness": 1.0, "Privacy & Data": 1.0}
    assert aegis_index(scores, weights) == pytest.approx(80.0)


def test_aegis_index_unequal_weights():
    # Fairness weight 2, Privacy weight 1 → (100*2 + 60*1) / 3 = 86.67
    scores = [("Fairness", 100.0), ("Privacy & Data", 60.0)]
    weights = {"Fairness": 2.0, "Privacy & Data": 1.0}
    assert aegis_index(scores, weights) == pytest.approx(260.0 / 3.0)


def test_aegis_index_empty_returns_zero():
    assert aegis_index([], {}) == pytest.approx(0.0)


def test_aegis_index_single_pillar():
    scores = [("Fairness", 72.5)]
    weights = {"Fairness": 1.0}
    assert aegis_index(scores, weights) == pytest.approx(72.5)


# --- Rule 9: Roll-up weighting (risk multipliers) ---


def test_risk_tier_multipliers_in_config():
    multipliers = CFG["risk_tier_multipliers"]
    assert multipliers["high"] == 1.5
    assert multipliers["limited"] == 1.0
    assert multipliers["minimal"] == 0.5
    assert multipliers["unacceptable"] == 2.0


def test_rollup_weighted_by_risk_tier():
    # high-risk system (1.5) scores 80, limited-risk (1.0) scores 40
    # expected = (80×1.5 + 40×1.0) / (1.5+1.0) = 160/2.5 = 64
    entries = [(80.0, 1.5), (40.0, 1.0)]
    total_w = sum(rm for _, rm in entries)
    result = sum(idx * rm for idx, rm in entries) / total_w
    assert result == pytest.approx(64.0)
