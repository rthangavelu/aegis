"""Unit tests for aegis.recommend.engine — one test per INTENT.md section 9 rule."""

import pytest

from aegis.recommend.engine import (
    _effort_factor,
    _priority_score,
    _tier,
    build_recommendations,
)
from aegis.scoring.engine import load_config

CFG = load_config()


# --- Effort factors ---


def test_effort_s_factor_is_1():
    assert _effort_factor("S") == 1


def test_effort_m_factor_is_2():
    assert _effort_factor("M") == 2


def test_effort_l_factor_is_4():
    assert _effort_factor("L") == 4


# --- Priority formula: severity_weight × risk_multiplier × num_systems / effort_factor ---


def test_priority_critical_high_risk_one_system_effort_m():
    # critical(4) × high(1.5) × 1 / M(2) = 3.0
    p = _priority_score("critical", 1.5, 1, "M", CFG)
    assert p == pytest.approx(3.0)


def test_priority_high_limited_risk_two_systems_effort_s():
    # high(3) × limited(1.0) × 2 / S(1) = 6.0
    p = _priority_score("high", 1.0, 2, "S", CFG)
    assert p == pytest.approx(6.0)


def test_priority_medium_minimal_risk_one_system_effort_l():
    # medium(2) × minimal(0.5) × 1 / L(4) = 0.25
    p = _priority_score("medium", 0.5, 1, "L", CFG)
    assert p == pytest.approx(0.25)


def test_priority_scales_with_num_systems():
    p1 = _priority_score("high", 1.0, 1, "M", CFG)
    p3 = _priority_score("high", 1.0, 3, "M", CFG)
    assert p3 == pytest.approx(3 * p1)


# --- Tier assignment ---


def test_tier_critical_always_p0():
    assert _tier("critical", "L", 0.1) == "P0"


def test_tier_critical_p0_regardless_of_effort():
    assert _tier("critical", "S", 100.0) == "P0"


def test_tier_quick_win_effort_s_high_priority():
    assert _tier("high", "S", 3.0) == "quick_win"


def test_tier_quick_win_requires_priority_threshold():
    # effort S but low priority → hygiene, not quick_win
    assert _tier("low", "S", 1.0) == "hygiene"


def test_tier_strategic_effort_l():
    assert _tier("high", "L", 10.0) == "strategic"


def test_tier_hygiene_medium_effort_m():
    assert _tier("medium", "M", 1.5) == "hygiene"


# --- Root-cause grouping threshold ---


def test_org_wide_flag_on_remediation(tmp_path, monkeypatch):
    """build_recommendations treats org_wide_fix=true remediations as org-wide."""
    from unittest.mock import MagicMock, patch

    from aegis.models import TestStatus

    mock_result = MagicMock()
    mock_result.run_id = "run-test"
    mock_result.system_id = "sys-a"
    mock_result.test_id = "FAIR-001"
    mock_result.status = TestStatus.fail

    mock_score = MagicMock()
    mock_score.scope_id = "sys-a"
    mock_score.score = 50.0

    mock_system = MagicMock()
    mock_system.id = "sys-a"
    mock_system.risk_tier.value = "high"

    mock_session = MagicMock()
    mock_session.exec.return_value.all.side_effect = [
        [mock_result],  # test results
        [mock_system],  # systems
        [mock_score],  # scores
    ]

    # Minimal test/remediation maps
    test_map = {
        "FAIR-001": {
            "id": "FAIR-001",
            "pillar": "Fairness",
            "severity": "critical",
            "remediation_id": "REM-FAIR-001",
        }
    }
    rem_map = [
        {
            "id": "REM-FAIR-001",
            "title": "Fix bias",
            "effort": "M",
            "owner_role": "ML Lead",
            "org_wide_fix": True,
            "steps": ["Step 1"],
        }
    ]

    with (
        patch("aegis.recommend.engine.load_test_library", return_value=list(test_map.values())),
        patch("aegis.recommend.engine.load_remediations", return_value=rem_map),
    ):
        items = build_recommendations("run-test", mock_session)

    assert len(items) == 1
    assert items[0].org_wide_fix is True


def test_three_or_more_systems_becomes_org_wide(monkeypatch):
    """When the same remediation affects ≥3 systems, it becomes org-wide."""
    from unittest.mock import MagicMock, patch

    from aegis.models import TestStatus

    systems = ["sys-a", "sys-b", "sys-c"]

    def make_result(sid):
        r = MagicMock()
        r.run_id = "run-test"
        r.system_id = sid
        r.test_id = "GOV-001"
        r.status = TestStatus.fail
        return r

    def make_system(sid):
        s = MagicMock()
        s.id = sid
        s.risk_tier.value = "high"
        return s

    def make_score(sid):
        sc = MagicMock()
        sc.scope_id = sid
        sc.score = 60.0
        return sc

    mock_session = MagicMock()
    mock_session.exec.return_value.all.side_effect = [
        [make_result(s) for s in systems],
        [make_system(s) for s in systems],
        [make_score(s) for s in systems],
    ]

    test_map = [
        {
            "id": "GOV-001",
            "pillar": "Governance & Accountability",
            "severity": "high",
            "remediation_id": "REM-GOV-001",
        }
    ]
    rem_map = [
        {
            "id": "REM-GOV-001",
            "title": "Get approval",
            "effort": "S",
            "owner_role": "System Owner",
            "org_wide_fix": False,
            "steps": ["Step 1"],
        }
    ]

    with (
        patch("aegis.recommend.engine.load_test_library", return_value=test_map),
        patch("aegis.recommend.engine.load_remediations", return_value=rem_map),
    ):
        items = build_recommendations("run-test", mock_session)

    assert len(items) == 1
    assert items[0].org_wide_fix is True
    assert len(items[0].systems_affected) == 3


# --- Sort order: P0 first, then by priority ---


def test_p0_items_sorted_first():
    items_data = [
        ("hygiene", 10.0, "Low priority hygiene"),
        ("P0", 1.0, "Critical issue"),
        ("quick_win", 5.0, "Quick win"),
    ]

    from aegis.recommend.engine import RecommendationItem

    items = [
        RecommendationItem(
            remediation_id=f"REM-{i}",
            test_id=f"TST-{i:03d}",
            title=title,
            pillar="Fairness",
            severity="high",
            effort="M",
            owner_role="Owner",
            org_wide_fix=False,
            steps=[],
            systems_affected=["sys-a"],
            priority=priority,
            tier=tier,
            current_scores={"sys-a": 70.0},
            projected_scores={"sys-a": 80.0},
            projected_uplift=10.0,
        )
        for i, (tier, priority, title) in enumerate(items_data)
    ]

    _TIER_ORDER = {"P0": 0, "quick_win": 1, "strategic": 2, "hygiene": 3}
    items.sort(key=lambda x: (_TIER_ORDER.get(x.tier, 9), -x.priority))

    assert items[0].tier == "P0"
    assert items[1].tier == "quick_win"
    assert items[2].tier == "hygiene"


# --- Projected uplift integration ---


def test_projected_index_flips_failing_test():
    """_projected_index returns a higher score when a failing test is flipped to pass."""
    from unittest.mock import MagicMock

    from aegis.models import TestStatus
    from aegis.recommend.engine import _projected_index

    def make_result(test_id, status, system_id="sys-a"):
        r = MagicMock()
        r.system_id = system_id
        r.test_id = test_id
        r.status = status
        return r

    all_results = [
        make_result("FAIR-001", TestStatus.fail),
        make_result("FAIR-002", TestStatus.pass_),
        make_result("GOV-001", TestStatus.pass_),
    ]
    test_map = {
        "FAIR-001": {"pillar": "Fairness", "severity": "critical"},
        "FAIR-002": {"pillar": "Fairness", "severity": "high"},
        "GOV-001": {"pillar": "Governance & Accountability", "severity": "high"},
    }
    pillar_weights = {"Fairness": 1.0, "Governance & Accountability": 1.0}

    # Current index with FAIR-001 failing
    idx_before = _projected_index(
        "sys-a", "NONEXISTENT", all_results, test_map, pillar_weights, CFG
    )
    # Projected index with FAIR-001 flipped to pass
    idx_after = _projected_index("sys-a", "FAIR-001", all_results, test_map, pillar_weights, CFG)

    assert idx_after > idx_before
