"""Evidence runner — checks that a document exists, is current, and has required sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from aegis.models import AISystem

_TODAY = date(2026, 11, 14)  # fixed for deterministic mock runs


@dataclass
class EvidenceResult:
    status: str
    evidence_uri: Optional[str] = None
    message: Optional[str] = None


def _interpolate(template: str, system: AISystem) -> str:
    return template.replace("${system.id}", system.id).replace(
        "${system.eval_dataset}", system.eval_dataset or ""
    )


def _parse_last_updated(content: str) -> Optional[date]:
    m = re.search(r"\*\*Last updated:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    if m:
        return date.fromisoformat(m.group(1))
    return None


def _has_section(content: str, section_name: str) -> bool:
    pattern = r"^#{1,3}\s+" + re.escape(section_name)
    return bool(re.search(pattern, content, re.MULTILINE | re.IGNORECASE))


def run(test: dict, system: AISystem, pkg_dir: Path) -> EvidenceResult:
    check = test["check"]
    source_tmpl = check.get("source", "")
    source_rel = _interpolate(source_tmpl, system)
    doc_path = pkg_dir / source_rel

    if not doc_path.exists():
        return EvidenceResult(
            status="fail",
            evidence_uri=str(doc_path),
            message=f"Document not found: {source_rel}",
        )

    content = doc_path.read_text()
    rules = check.get("rules", {})

    max_age = rules.get("max_age_days")
    if max_age is not None:
        last_updated = _parse_last_updated(content)
        if last_updated is None:
            age_days = 0  # file just created — treat as fresh
        else:
            age_days = (_TODAY - last_updated).days
        if age_days > max_age:
            return EvidenceResult(
                status="fail",
                evidence_uri=str(doc_path),
                message=f"Document is {age_days} days old (max {max_age})",
            )

    required = rules.get("required_sections", [])
    missing = [s for s in required if not _has_section(content, s)]
    if missing:
        return EvidenceResult(
            status="fail",
            evidence_uri=str(doc_path),
            message=f"Missing required sections: {missing}",
        )

    return EvidenceResult(
        status="pass",
        evidence_uri=str(doc_path),
        message=f"Document present and valid: {source_rel}",
    )
