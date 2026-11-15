"""Tests for aegis.engine.runners.process."""

from aegis.engine.runners.process import run
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


def _test(ticket_type: str, rule: str = "") -> dict:
    return {
        "id": "TST-PROC",
        "type": "process",
        "inputs": {"ticket_type": ticket_type},
        "check": {"ticket_type": ticket_type, "rule": rule},
    }


TICKETS = [
    # deployment_approval: credit-scoring-v3 approved, resume-screener missing
    {
        "id": "TICK-001",
        "system_id": "credit-scoring-v3",
        "ticket_type": "deployment_approval",
        "approver": "cro@example.com",
        "approval_date": "2026-09-15",
        "deploy_date": "2026-09-18",
        "status": "approved",
    },
    {
        "id": "TICK-002",
        "system_id": "resume-screener",
        "ticket_type": "deployment_approval",
        "approver": None,
        "approval_date": None,
        "deploy_date": "2026-10-01",
        "status": "missing",
    },
    # bias_review: credit-scoring-v3 approved, resume-screener missing
    {
        "id": "TICK-004",
        "system_id": "credit-scoring-v3",
        "ticket_type": "bias_review",
        "approval_date": "2026-10-01",
        "deploy_date": None,
        "status": "approved",
    },
    {
        "id": "TICK-005",
        "system_id": "resume-screener",
        "ticket_type": "bias_review",
        "approval_date": None,
        "deploy_date": None,
        "status": "missing",
    },
    # security_risk_assessment: credit-scoring-v3 approved
    {
        "id": "TICK-006",
        "system_id": "credit-scoring-v3",
        "ticket_type": "security_risk_assessment",
        "approval_date": "2026-09-10",
        "deploy_date": None,
        "status": "approved",
    },
    # org-wide policy_acknowledgment
    {
        "id": "TICK-009",
        "system_id": "org",
        "ticket_type": "policy_acknowledgment",
        "approval_date": "2026-10-01",
        "deploy_date": None,
        "status": "acknowledged",
    },
]


def test_deployment_approval_pass_credit_scoring():
    t = _test(
        "deployment_approval", rule="approval.date < deploy.date AND approval.status == 'approved'"
    )
    result = run(t, _system("credit-scoring-v3"), TICKETS)
    assert result.status == "pass"


def test_deployment_approval_fail_resume_screener():
    t = _test(
        "deployment_approval", rule="approval.date < deploy.date AND approval.status == 'approved'"
    )
    result = run(t, _system("resume-screener"), TICKETS)
    assert result.status == "fail"


def test_bias_review_pass_credit_scoring():
    t = _test("bias_review")
    result = run(t, _system("credit-scoring-v3"), TICKETS)
    assert result.status == "pass"


def test_bias_review_fail_resume_screener():
    t = _test("bias_review")
    result = run(t, _system("resume-screener"), TICKETS)
    assert result.status == "fail"


def test_security_risk_assessment_pass():
    t = _test("security_risk_assessment")
    result = run(t, _system("credit-scoring-v3"), TICKETS)
    assert result.status == "pass"


def test_no_matching_ticket_fails():
    t = _test("deployment_approval")
    result = run(t, _system("unknown-system"), TICKETS)
    assert result.status == "fail"
    assert "No" in result.message


def test_org_wide_ticket_matches_any_system():
    t = _test("policy_acknowledgment")
    result = run(t, _system("resume-screener"), TICKETS)
    assert result.status == "pass"
