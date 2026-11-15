"""Executor — dispatches tests to runners, hashes evidence, stores results."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from sqlmodel import Session

from aegis.engine.runners import attestation, evidence, process, technical
from aegis.engine.selector import applies_to
from aegis.models import AISystem, TestResult, TestRun, TestStatus, Trigger

_PKG_DIR = Path(__file__).parent.parent
_SEED_DIR = _PKG_DIR / "seed"


def _load_seed(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _make_na(run_id: str, system: AISystem, test: dict) -> TestResult:
    return TestResult(
        run_id=run_id,
        system_id=system.id,
        test_id=test["id"],
        status=TestStatus.na,
        message="Not applicable to this system",
        executed_at=_now(),
    )


def _make_error(run_id: str, system: AISystem, test: dict, msg: str) -> TestResult:
    return TestResult(
        run_id=run_id,
        system_id=system.id,
        test_id=test["id"],
        status=TestStatus.error,
        message=msg,
        executed_at=_now(),
    )


def _status_enum(s: str) -> TestStatus:
    mapping = {
        "pass": TestStatus.pass_,
        "warn": TestStatus.warn,
        "fail": TestStatus.fail,
        "na": TestStatus.na,
        "pending": TestStatus.pending,
        "error": TestStatus.error,
    }
    return mapping.get(s, TestStatus.error)


def _run_one(
    test: dict,
    system: AISystem,
    tickets: list[dict],
    attestations: list[dict],
) -> tuple[str, Optional[float], Optional[str], Optional[str], Optional[str]]:
    """Return (status, metric_value, evidence_uri, evidence_hash, message)."""
    test_type = test.get("type")

    if test_type == "technical":
        r = technical.run(test, system, _PKG_DIR)
        ev_hash = _sha256(r.evidence_uri or "") if r.evidence_uri else None
        return r.status, r.metric_value, r.evidence_uri, ev_hash, r.message

    elif test_type == "evidence":
        r = evidence.run(test, system, _PKG_DIR)
        ev_hash = None
        if r.evidence_uri and Path(r.evidence_uri).exists():
            ev_hash = _sha256(Path(r.evidence_uri).read_text())
        return r.status, None, r.evidence_uri, ev_hash, r.message

    elif test_type == "process":
        r = process.run(test, system, tickets)
        return r.status, None, r.evidence_uri, None, r.message

    elif test_type == "attestation":
        r = attestation.run(test, system, attestations)
        ev_hash = _sha256(r.evidence_uri) if r.evidence_uri else None
        return r.status, None, r.evidence_uri, ev_hash, r.message

    else:
        return "error", None, None, None, f"Unknown test type: {test_type!r}"


def execute_run(
    systems: list[AISystem],
    tests: list[dict],
    session: Session,
    trigger: Trigger = Trigger.manual,
    scope: str = "all",
) -> TestRun:
    tickets = _load_seed(_SEED_DIR / "tickets.yaml").get("tickets", [])
    attestations_data = _load_seed(_SEED_DIR / "attestations.yaml").get("attestations", [])

    run_id = f"run-{_now().strftime('%Y%m%dT%H%M%S')}"
    run = TestRun(id=run_id, started_at=_now(), trigger=trigger, scope=scope)
    session.add(run)

    for system in systems:
        for test in tests:
            if not applies_to(test, system):
                result = _make_na(run_id, system, test)
            else:
                try:
                    status_str, metric, ev_uri, ev_hash, msg = _run_one(
                        test, system, tickets, attestations_data
                    )
                    result = TestResult(
                        run_id=run_id,
                        system_id=system.id,
                        test_id=test["id"],
                        status=_status_enum(status_str),
                        metric_value=metric,
                        threshold=str(test.get("check", {}).get("threshold", "")),
                        evidence_uri=ev_uri,
                        evidence_hash=ev_hash,
                        message=msg,
                        executed_at=_now(),
                    )
                except Exception as exc:  # noqa: BLE001
                    result = _make_error(run_id, system, test, str(exc))

            session.add(result)

    run.finished_at = _now()
    session.commit()
    return run
