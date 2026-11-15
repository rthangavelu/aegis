"""Attestation runner — reads questionnaire answers from seed data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from aegis.models import AISystem

_TODAY = date(2026, 11, 14)


@dataclass
class AttestationResult:
    status: str
    evidence_uri: Optional[str] = None
    message: Optional[str] = None


def run(test: dict, system: AISystem, attestations: list[dict]) -> AttestationResult:
    check = test["check"]
    question_id = check.get("question_id") or f"ATTEST-{test['id']}"
    expires_days = check.get("expires_days", 365)

    matches = [
        a
        for a in attestations
        if a.get("system_id") == system.id and a.get("question_id") == question_id
    ]

    if not matches:
        return AttestationResult(
            status="pending", message=f"No attestation found for {question_id}"
        )

    att = matches[0]
    answer = att.get("answer")

    if answer is None:
        return AttestationResult(
            status="pending",
            message=f"Attestation {question_id} not yet answered",
        )

    answered_at_str = att.get("answered_at")
    if answered_at_str:
        answered_at = date.fromisoformat(str(answered_at_str))
        age_days = (_TODAY - answered_at).days
        if age_days > expires_days:
            return AttestationResult(
                status="fail",
                evidence_uri=att.get("evidence_uri"),
                message=f"Attestation expired ({age_days} days old, limit {expires_days})",
            )

    if answer is False:
        return AttestationResult(
            status="fail",
            evidence_uri=att.get("evidence_uri"),
            message=f"Attestation {question_id}: answered NO",
        )

    return AttestationResult(
        status="pass",
        evidence_uri=att.get("evidence_uri"),
        message=f"Attestation {question_id}: confirmed by {att.get('answered_by')}",
    )
