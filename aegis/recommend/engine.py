"""Recommendation engine — implements INTENT.md section 9 rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from aegis.engine.loader import load_remediations, load_test_library
from aegis.models import AISystem, Score, TestResult, TestStatus
from aegis.scoring.engine import (
    _has_scored_results,
    aegis_index,
    load_config,
    pillar_score,
    severity_weight,
)

_PKG_DIR = Path(__file__).parent.parent
_TESTLIB_DIR = _PKG_DIR / "testlib"
_REMEDIATION_DIR = _PKG_DIR / "remediation"

_EFFORT_FACTOR = {"S": 1, "M": 2, "L": 4}

_FAIL_STATUSES = {TestStatus.fail, TestStatus.error}
_SCORED_STATUSES = {TestStatus.pass_, TestStatus.warn, TestStatus.fail, TestStatus.error}


@dataclass
class RecommendationItem:
    remediation_id: str
    test_id: str
    title: str
    pillar: str
    severity: str
    effort: str
    owner_role: str
    org_wide_fix: bool
    steps: list[str]
    systems_affected: list[str]
    priority: float
    tier: str
    current_scores: dict[str, float]  # system_id → current aegis index
    projected_scores: dict[str, float]  # system_id → projected aegis index after fix
    projected_uplift: float  # average uplift across affected systems


def _effort_factor(effort: str) -> int:
    return _EFFORT_FACTOR.get(effort, 2)


def _priority_score(
    severity: str,
    risk_multiplier: float,
    num_systems: int,
    effort: str,
    cfg: dict,
) -> float:
    w = severity_weight(severity, cfg)
    return w * risk_multiplier * num_systems / _effort_factor(effort)


def _tier(severity: str, effort: str, priority: float) -> str:
    if severity == "critical":
        return "P0"
    if effort == "S" and priority >= 2.0:
        return "quick_win"
    if effort == "L":
        return "strategic"
    return "hygiene"


def _projected_index(
    system_id: str,
    test_id: str,
    all_results: list[TestResult],
    test_map: dict,
    pillar_weights: dict,
    cfg: dict,
) -> float:
    """Return the Aegis Index for a system if test_id were flipped to pass."""
    by_pillar: dict[str, list] = {}
    for r in all_results:
        if r.system_id != system_id:
            continue
        t = test_map.get(r.test_id)
        if not t:
            continue
        # Flip the target test to pass for the projection
        status = TestStatus.pass_ if r.test_id == test_id else r.status
        by_pillar.setdefault(t["pillar"], []).append((status, t["severity"]))

    per_pillar = []
    for pillar, pairs in by_pillar.items():
        # Build lightweight pairs for scoring
        class _R:
            def __init__(self, s):
                self.status = s

        rich_pairs = [(_R(s), {"severity": sev}) for s, sev in pairs]
        if not _has_scored_results(rich_pairs):
            continue
        ps = pillar_score(rich_pairs, cfg)
        per_pillar.append((pillar, ps))

    return aegis_index(per_pillar, pillar_weights)


def build_recommendations(run_id: str, session: Session) -> list[RecommendationItem]:
    cfg = load_config()
    tests = load_test_library(_TESTLIB_DIR)
    test_map = {t["id"]: t for t in tests}
    remediations = load_remediations(_REMEDIATION_DIR)
    rem_map = {r["id"]: r for r in remediations}
    pillar_weights: dict[str, float] = cfg.get("pillar_weights", {})

    all_results: list[TestResult] = session.exec(
        select(TestResult).where(TestResult.run_id == run_id)
    ).all()
    systems: list[AISystem] = session.exec(select(AISystem)).all()
    system_map = {s.id: s for s in systems}

    # Current aegis indices from stored scores
    current_scores: dict[str, float] = {}
    stored_scores = session.exec(
        select(Score).where(
            Score.run_id == run_id, Score.pillar == "overall", Score.scope == "system"
        )
    ).all()
    for sc in stored_scores:
        current_scores[sc.scope_id] = sc.score

    # Collect failing/warning results, grouped by test_id
    failing: dict[str, list[str]] = {}  # test_id → [system_id, ...]
    for r in all_results:
        if r.status not in _FAIL_STATUSES:
            continue
        failing.setdefault(r.test_id, []).append(r.system_id)

    # Group by remediation_id to merge duplicate remediations across systems
    by_rem: dict[str, dict] = {}  # rem_id → {test_ids, system_ids, ...}
    for test_id, sys_ids in failing.items():
        t = test_map.get(test_id)
        if not t:
            continue
        rem_id = t.get("remediation_id", "")
        if not rem_id:
            continue
        rem = rem_map.get(rem_id)
        if not rem:
            continue

        if rem_id not in by_rem:
            by_rem[rem_id] = {
                "rem": rem,
                "test_ids": [],
                "system_ids": set(),
                "severity": t["severity"],
                "pillar": t["pillar"],
            }
        by_rem[rem_id]["test_ids"].append(test_id)
        by_rem[rem_id]["system_ids"].update(sys_ids)
        # Escalate severity if any test is worse
        _SEV_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        if _SEV_ORDER.get(t["severity"], 0) > _SEV_ORDER.get(by_rem[rem_id]["severity"], 0):
            by_rem[rem_id]["severity"] = t["severity"]

    items: list[RecommendationItem] = []
    for rem_id, entry in by_rem.items():
        rem = entry["rem"]
        sys_ids = sorted(entry["system_ids"])
        severity = entry["severity"]
        effort = rem.get("effort", "M")
        test_ids = entry["test_ids"]
        # Use the first (or only) test_id as the representative
        primary_test_id = test_ids[0]

        # Determine risk multiplier: use the max across affected systems
        risk_mult = max(
            cfg["risk_tier_multipliers"].get(system_map[sid].risk_tier.value, 1.0)
            for sid in sys_ids
            if sid in system_map
        )

        # Root-cause grouping: org-wide if org_wide_fix OR affects ≥3 systems
        is_org_wide = rem.get("org_wide_fix", False) or len(sys_ids) >= 3

        priority = _priority_score(severity, risk_mult, len(sys_ids), effort, cfg)
        tier = _tier(severity, effort, priority)

        # Projected uplift per affected system
        proj: dict[str, float] = {}
        for sid in sys_ids:
            proj[sid] = _projected_index(
                sid, primary_test_id, all_results, test_map, pillar_weights, cfg
            )

        cur = {sid: current_scores.get(sid, 0.0) for sid in sys_ids}
        avg_uplift = sum(proj[sid] - cur[sid] for sid in sys_ids) / len(sys_ids) if sys_ids else 0.0

        items.append(
            RecommendationItem(
                remediation_id=rem_id,
                test_id=primary_test_id,
                title=rem.get("title", rem_id),
                pillar=entry["pillar"],
                severity=severity,
                effort=effort,
                owner_role=rem.get("owner_role", ""),
                org_wide_fix=is_org_wide,
                steps=rem.get("steps", []),
                systems_affected=sys_ids,
                priority=round(priority, 2),
                tier=tier,
                current_scores=cur,
                projected_scores=proj,
                projected_uplift=round(avg_uplift, 1),
            )
        )

    # Sort: P0 first, then by priority descending
    _TIER_ORDER = {"P0": 0, "quick_win": 1, "strategic": 2, "hygiene": 3}
    items.sort(key=lambda x: (_TIER_ORDER.get(x.tier, 9), -x.priority))
    return items


def render_markdown(items: list[RecommendationItem], run_id: str) -> str:
    lines = [
        "# Aegis Improvement Plan",
        "",
        f"**Run:** `{run_id}`  ",
        "**Status:** MOCK DATA — for demonstration only",
        "",
    ]

    _TIER_LABEL = {
        "P0": "P0 — Critical (fix immediately)",
        "quick_win": "Quick Wins (high impact, low effort)",
        "strategic": "Strategic (high effort, significant uplift)",
        "hygiene": "Hygiene (lower priority)",
    }

    _HORIZON = {
        "P0": "30 days",
        "quick_win": "30 days",
        "strategic": "90 days",
        "hygiene": "60 days",
    }

    current_tier = None
    for item in items:
        if item.tier != current_tier:
            current_tier = item.tier
            lines += ["", f"## {_TIER_LABEL.get(item.tier, item.tier)}", ""]

        scope = "org-wide" if item.org_wide_fix else ", ".join(item.systems_affected)
        horizon = _HORIZON.get(item.tier, "60 days")

        lines += [
            f"### {item.title}",
            "",
            "| | |",
            "|---|---|",
            f"| **Test** | `{item.test_id}` |",
            f"| **Pillar** | {item.pillar} |",
            f"| **Severity** | {item.severity} |",
            f"| **Effort** | {item.effort} |",
            f"| **Owner** | {item.owner_role} |",
            f"| **Scope** | {scope} |",
            f"| **Priority score** | {item.priority} |",
            f"| **Projected uplift** | +{item.projected_uplift:.1f} pts avg |",
            f"| **Target horizon** | {horizon} |",
            "",
        ]

        if item.current_scores:
            lines.append("**Index before → after:**")
            lines.append("")
            for sid in item.systems_affected:
                cur = item.current_scores.get(sid, 0.0)
                proj = item.projected_scores.get(sid, cur)
                delta = proj - cur
                sign = "+" if delta >= 0 else ""
                lines.append(f"- {sid}: {cur:.1f} → {proj:.1f} ({sign}{delta:.1f})")
            lines.append("")

        if item.steps:
            lines.append("**Steps:**")
            lines.append("")
            for i, step in enumerate(item.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

    # 30/60/90-day roadmap summary
    lines += [
        "---",
        "",
        "## 30 / 60 / 90-day roadmap",
        "",
        "| Horizon | Actions |",
        "|---|---|",
    ]
    buckets: dict[str, list[str]] = {"30 days": [], "60 days": [], "90 days": []}
    for item in items:
        h = _HORIZON.get(item.tier, "60 days")
        buckets[h].append(item.title)
    for horizon, titles in buckets.items():
        cell = "; ".join(titles) if titles else "—"
        lines.append(f"| **{horizon}** | {cell} |")

    lines.append("")
    return "\n".join(lines)
