"""Tests for the YAML loader and schema validator."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aegis.engine.loader import (
    load_remediations,
    load_systems,
    load_test_library,
    validate_remediation,
    validate_system,
    validate_test_case,
)

_PKG = Path(__file__).parent.parent / "aegis"
_TESTLIB = _PKG / "testlib"
_REMEDIATION = _PKG / "remediation"
_SEED_SYSTEMS = _PKG / "seed" / "systems.yaml"

_VALID_TEST_CASE: dict = {
    "id": "FAIR-001",
    "name": "Disparate impact",
    "description": "Selection rate ratio across groups.",
    "pillar": "Fairness",
    "type": "technical",
    "severity": "critical",
    "applies_to": {"risk_tier": ["high"]},
    "mappings": [{"framework": "NIST_AI_RMF", "ref": "MEASURE 2.11"}],
    "check": {"metric": "disparate_impact_ratio"},
    "remediation_id": "REM-FAIR-001",
    "owner_role": "ML Lead",
    "version": 1,
}

_VALID_REMEDIATION: dict = {
    "id": "REM-FAIR-001",
    "title": "Reduce disparate impact",
    "steps": ["Step 1", "Step 2"],
    "effort": "M",
    "owner_role": "ML Lead",
    "org_wide_fix": False,
}

_VALID_SYSTEM: dict = {
    "id": "test-system",
    "name": "Test System",
    "owner": "owner@example.com",
    "business_unit": "Engineering",
    "purpose": "Testing",
    "model_type": "classification",
    "risk_tier": "high",
    "lifecycle_stage": "production",
    "mock": True,
}


class TestValidateTestCase:
    def test_valid_case_passes(self):
        validate_test_case(_VALID_TEST_CASE)

    def test_missing_required_field_raises(self):
        bad = copy.deepcopy(_VALID_TEST_CASE)
        del bad["id"]
        with pytest.raises(ValueError, match="Invalid test case"):
            validate_test_case(bad)

    def test_invalid_pillar_raises(self):
        bad = copy.deepcopy(_VALID_TEST_CASE)
        bad["pillar"] = "NotAPillar"
        with pytest.raises(ValueError, match="Invalid test case"):
            validate_test_case(bad)

    def test_invalid_severity_raises(self):
        bad = copy.deepcopy(_VALID_TEST_CASE)
        bad["severity"] = "blocker"
        with pytest.raises(ValueError, match="Invalid test case"):
            validate_test_case(bad)

    def test_invalid_id_pattern_raises(self):
        bad = copy.deepcopy(_VALID_TEST_CASE)
        bad["id"] = "fair001"  # wrong pattern
        with pytest.raises(ValueError, match="Invalid test case"):
            validate_test_case(bad)

    def test_mappings_must_not_be_empty(self):
        bad = copy.deepcopy(_VALID_TEST_CASE)
        bad["mappings"] = []
        with pytest.raises(ValueError, match="Invalid test case"):
            validate_test_case(bad)


class TestValidateRemediation:
    def test_valid_remediation_passes(self):
        validate_remediation(_VALID_REMEDIATION)

    def test_missing_field_raises(self):
        bad = copy.deepcopy(_VALID_REMEDIATION)
        del bad["steps"]
        with pytest.raises(ValueError, match="Invalid remediation"):
            validate_remediation(bad)

    def test_invalid_effort_raises(self):
        bad = copy.deepcopy(_VALID_REMEDIATION)
        bad["effort"] = "XL"
        with pytest.raises(ValueError, match="Invalid remediation"):
            validate_remediation(bad)

    def test_id_must_start_with_rem(self):
        bad = copy.deepcopy(_VALID_REMEDIATION)
        bad["id"] = "FAIR-001"
        with pytest.raises(ValueError, match="Invalid remediation"):
            validate_remediation(bad)


class TestValidateSystem:
    def test_valid_system_passes(self):
        validate_system(_VALID_SYSTEM)

    def test_invalid_risk_tier_raises(self):
        bad = copy.deepcopy(_VALID_SYSTEM)
        bad["risk_tier"] = "critical"
        with pytest.raises(ValueError, match="Invalid system"):
            validate_system(bad)


class TestLoadTestLibrary:
    def test_loads_all_yaml_files(self):
        tests = load_test_library(_TESTLIB)
        assert len(tests) >= 4
        ids = [t["id"] for t in tests]
        assert "FAIR-001" in ids
        assert "GOV-001" in ids

    def test_each_test_has_source_key(self):
        tests = load_test_library(_TESTLIB)
        for t in tests:
            assert "_source" in t

    def test_raises_on_invalid_yaml_dir(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("id: bad\nname: missing fields\n")
        with pytest.raises(ValueError):
            load_test_library(tmp_path)


class TestLoadRemediations:
    def test_loads_all_yaml_files(self):
        remediations = load_remediations(_REMEDIATION)
        assert len(remediations) >= 3
        ids = [r["id"] for r in remediations]
        assert "REM-FAIR-001" in ids
        assert "REM-GOV-001" in ids

    def test_each_remediation_has_source_key(self):
        remediations = load_remediations(_REMEDIATION)
        for r in remediations:
            assert "_source" in r


class TestLoadSystems:
    def test_loads_seed_systems(self):
        systems = load_systems(_SEED_SYSTEMS)
        assert len(systems) == 3
        ids = [s["id"] for s in systems]
        assert "resume-screener" in ids
        assert "support-chatbot" in ids
        assert "credit-scoring-v3" in ids

    def test_all_systems_are_mock(self):
        systems = load_systems(_SEED_SYSTEMS)
        for s in systems:
            assert s["mock"] is True
