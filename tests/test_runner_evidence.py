"""Tests for aegis.engine.runners.evidence."""

from pathlib import Path

from aegis.engine.runners.evidence import run
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier

_PKG_DIR = Path(__file__).parent.parent / "aegis"


def _system(sys_id: str = "credit-scoring-v3") -> AISystem:
    return AISystem(
        id=sys_id,
        name="Test",
        owner="owner@example.com",
        business_unit="BU",
        purpose="Testing",
        model_type=ModelType.classification,
        risk_tier=RiskTier.high,
        lifecycle_stage=LifecycleStage.production,
    )


def _test(source: str, max_age_days: int | None = None, sections: list[str] | None = None) -> dict:
    rules: dict = {}
    if max_age_days is not None:
        rules["max_age_days"] = max_age_days
    if sections:
        rules["required_sections"] = sections
    return {
        "id": "TST-EV",
        "type": "evidence",
        "check": {"source": source, "rules": rules},
    }


# --- existing documents pass ---


def test_dpa_credit_scoring_passes():
    t = _test(
        "seed/documents/credit-scoring-v3_dpa.md",
        max_age_days=365,
        sections=["Data controller", "Retention"],
    )
    result = run(t, _system("credit-scoring-v3"), _PKG_DIR)
    assert result.status == "pass"


def test_monitoring_support_chatbot_passes():
    t = _test(
        "seed/documents/support-chatbot_monitoring.md",
        max_age_days=365,
        sections=["Metrics tracked"],
    )
    result = run(t, _system("support-chatbot"), _PKG_DIR)
    assert result.status == "pass"


def test_risk_assessment_credit_scoring_passes():
    t = _test(
        "seed/documents/credit-scoring-v3_risk_assessment.md",
        max_age_days=365,
        sections=["Risk identification"],
    )
    result = run(t, _system("credit-scoring-v3"), _PKG_DIR)
    assert result.status == "pass"


# --- missing document fails ---


def test_missing_document_fails():
    t = _test("seed/documents/does_not_exist.md")
    result = run(t, _system(), _PKG_DIR)
    assert result.status == "fail"
    assert "not found" in result.message.lower()


# --- stale document fails ---


def test_stale_document_fails(tmp_path):
    doc = tmp_path / "stale.md"
    doc.write_text("# Stale\n\n**Last updated:** 2020-01-01\n\n## Section A\nContent.\n")
    t = {
        "id": "TST-STALE",
        "type": "evidence",
        "check": {
            "source": str(doc),
            "rules": {"max_age_days": 365},
        },
    }
    result = run(t, _system(), _PKG_DIR)
    assert result.status == "fail"
    assert "days old" in result.message


# --- missing required section fails ---


def test_missing_section_fails(tmp_path):
    doc = tmp_path / "nodpa.md"
    doc.write_text("# DPA\n\n**Last updated:** 2026-10-01\n\n## Retention\nContent.\n")
    t = {
        "id": "TST-SEC",
        "type": "evidence",
        "check": {
            "source": str(doc),
            "rules": {"required_sections": ["Data sources", "Retention"]},
        },
    }
    result = run(t, _system(), _PKG_DIR)
    assert result.status == "fail"
    assert "Data sources" in result.message


# --- system id interpolation ---


def test_system_id_interpolation(tmp_path):
    doc = tmp_path / "my-system_doc.md"
    doc.write_text("# Doc\n\n**Last updated:** 2026-10-01\n\n## Purpose\nContent.\n")
    t = _test(str(doc).replace("my-system", "${system.id}"))
    result = run(t, _system("my-system"), _PKG_DIR)
    # Proves interpolation replaced the placeholder and found the file
    assert result.status == "pass"
    assert "${system.id}" not in (result.evidence_uri or "")


def test_system_id_interpolation_missing():
    t = _test("seed/documents/${system.id}_dpa.md")
    result = run(t, _system("resume-screener"), _PKG_DIR)
    # Interpolation happens but file doesn't exist → fail
    assert result.status == "fail"
    assert "${system.id}" not in (result.evidence_uri or "")
