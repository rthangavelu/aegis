"""Process runner — checks tickets and approvals from seed data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aegis.models import AISystem


@dataclass
class ProcessResult:
    status: str
    evidence_uri: Optional[str] = None
    message: Optional[str] = None


def _find_tickets(tickets: list[dict], system_id: str, ticket_type: str) -> list[dict]:
    return [
        t
        for t in tickets
        if t.get("ticket_type") == ticket_type
        and (t.get("system_id") == system_id or t.get("system_id") in (None, "org"))
    ]


def run(test: dict, system: AISystem, tickets: list[dict]) -> ProcessResult:
    check = test["check"]
    ticket_type = test.get("inputs", {}).get("ticket_type") or check.get("ticket_type", "")
    rule = check.get("rule", "")

    matches = _find_tickets(tickets, system.id, ticket_type)

    if not matches:
        return ProcessResult(
            status="fail",
            message=f"No {ticket_type!r} ticket found for {system.id}",
        )

    # Evaluate the rule against the first matching ticket.
    ticket = matches[0]
    evidence_uri = f"seed/tickets/{ticket.get('id', 'unknown')}"

    if "approval.date < deploy.date" in rule:
        if ticket.get("status") != "approved":
            return ProcessResult(
                status="fail",
                evidence_uri=evidence_uri,
                message=f"Ticket {ticket['id']}: status is {ticket.get('status')!r}, expected 'approved'",
            )
        if ticket.get("approval_date") is None:
            return ProcessResult(
                status="fail",
                evidence_uri=evidence_uri,
                message=f"Ticket {ticket['id']}: approval_date is missing",
            )
        if ticket.get("approval_date") >= ticket.get("deploy_date", "9999-99-99"):
            return ProcessResult(
                status="fail",
                evidence_uri=evidence_uri,
                message=f"Ticket {ticket['id']}: approval_date not before deploy_date",
            )

    elif ticket.get("status") not in ("approved", "completed", "acknowledged"):
        return ProcessResult(
            status="fail",
            evidence_uri=evidence_uri,
            message=f"Ticket {ticket['id']}: status is {ticket.get('status')!r}",
        )

    return ProcessResult(
        status="pass",
        evidence_uri=evidence_uri,
        message=f"Ticket {ticket['id']} confirms {ticket_type}",
    )
