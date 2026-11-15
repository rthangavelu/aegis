"""Tests for aegis.engine.runners.attestation."""

from aegis.engine.runners.attestation import run
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier


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


def _test(question_id: str, expires_days: int = 365) -> dict:
    return {
        "id": question_id.replace("ATTEST-", ""),
        "type": "attestation",
        "check": {"question_id": question_id, "expires_days": expires_days},
    }


ATTESTATIONS = [
    # HUM-001: credit-scoring-v3 → true, resume-screener → null (pending)
    {
        "system_id": "credit-scoring-v3",
        "question_id": "ATTEST-HUM-001",
        "answer": True,
        "answered_by": "risk-lead@example.com",
        "answered_at": "2026-10-15",
        "expires_days": 90,
    },
    {
        "system_id": "resume-screener",
        "question_id": "ATTEST-HUM-001",
        "answer": None,
        "answered_by": None,
        "answered_at": None,
        "expires_days": 90,
    },
    # GOV-003: credit-scoring-v3 → true, resume-screener → null
    {
        "system_id": "credit-scoring-v3",
        "question_id": "ATTEST-GOV-003",
        "answer": True,
        "answered_by": "risk-lead@example.com",
        "answered_at": "2026-09-18",
        "expires_days": 365,
    },
    {
        "system_id": "resume-screener",
        "question_id": "ATTEST-GOV-003",
        "answer": None,
        "answered_by": None,
        "answered_at": None,
        "expires_days": 365,
    },
    # Expired attestation
    {
        "system_id": "support-chatbot",
        "question_id": "ATTEST-EXP-001",
        "answer": True,
        "answered_by": "cx-lead@example.com",
        "answered_at": "2024-01-01",
        "expires_days": 90,
    },
    # Explicit NO
    {
        "system_id": "support-chatbot",
        "question_id": "ATTEST-NO-001",
        "answer": False,
        "answered_by": "cx-lead@example.com",
        "answered_at": "2026-10-01",
        "expires_days": 365,
    },
    # CULT-001: all three systems → true
    {
        "system_id": "credit-scoring-v3",
        "question_id": "ATTEST-CULT-001",
        "answer": True,
        "answered_by": "ai-governance@example.com",
        "answered_at": "2026-10-01",
        "expires_days": 365,
    },
    {
        "system_id": "support-chatbot",
        "question_id": "ATTEST-CULT-001",
        "answer": True,
        "answered_by": "ai-governance@example.com",
        "answered_at": "2026-10-01",
        "expires_days": 365,
    },
    {
        "system_id": "resume-screener",
        "question_id": "ATTEST-CULT-001",
        "answer": True,
        "answered_by": "ai-governance@example.com",
        "answered_at": "2026-10-01",
        "expires_days": 365,
    },
]


def test_pass_when_true():
    t = _test("ATTEST-HUM-001")
    result = run(t, _system("credit-scoring-v3"), ATTESTATIONS)
    assert result.status == "pass"


def test_pending_when_null_answer():
    t = _test("ATTEST-HUM-001")
    result = run(t, _system("resume-screener"), ATTESTATIONS)
    assert result.status == "pending"


def test_pending_when_no_attestation_found():
    t = _test("ATTEST-NONEXISTENT")
    result = run(t, _system("credit-scoring-v3"), ATTESTATIONS)
    assert result.status == "pending"


def test_fail_when_answer_false():
    t = _test("ATTEST-NO-001")
    result = run(t, _system("support-chatbot"), ATTESTATIONS)
    assert result.status == "fail"
    assert "NO" in result.message


def test_fail_when_expired():
    t = _test("ATTEST-EXP-001", expires_days=90)
    result = run(t, _system("support-chatbot"), ATTESTATIONS)
    assert result.status == "fail"
    assert "expired" in result.message.lower()


def test_pass_cult_all_three_systems():
    t = _test("ATTEST-CULT-001")
    for sys_id in ("credit-scoring-v3", "support-chatbot", "resume-screener"):
        result = run(t, _system(sys_id), ATTESTATIONS)
        assert result.status == "pass", f"Expected pass for {sys_id}, got {result.status}"


def test_gov_003_pending_resume_screener():
    t = _test("ATTEST-GOV-003")
    result = run(t, _system("resume-screener"), ATTESTATIONS)
    assert result.status == "pending"


def test_gov_003_pass_credit_scoring():
    t = _test("ATTEST-GOV-003")
    result = run(t, _system("credit-scoring-v3"), ATTESTATIONS)
    assert result.status == "pass"
