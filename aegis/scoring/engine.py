"""Scoring engine — implements INTENT.md section 8 rules."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlmodel import Session, select

from aegis.engine.loader import load_test_library
from aegis.models import AISystem, RAGStatus, Score, TestResult, TestStatus

_PKG_DIR = Path(__file__).parent.parent
_TESTLIB_DIR = _PKG_DIR / "testlib"
_CONFIG_PATH = Path(__file__).parent / "config.yaml"

_SCORED_STATUSES = {TestStatus.pass_, TestStatus.warn, TestStatus.fail, TestStatus.error}


def load_config() -> dict:
    return yaml.safe_load(_CONFIG_PATH.read_text())


def status_points(status: TestStatus, cfg: dict) -> float:
    """Return scoring points for a result status."""
    mapping = {
        TestStatus.pass_: cfg["status_points"]["pass"],
        TestStatus.warn: cfg["status_points"]["warn"],
        TestStatus.fail: cfg["status_points"]["fail"],
        TestStatus.error: cfg["status_points"]["error"],
    }
    return mapping.get(status, 0.0)


def severity_weight(severity: str, cfg: dict) -> int:
    return cfg["severity_weights"].get(severity, 1)


def pillar_score(pairs: list[tuple[TestResult, dict]], cfg: dict) -> float:
    """100 × Σ(points × severity_weight) / Σ(severity_weight), excluding na/pending."""
    total_w = 0
    total_pts = 0.0
    for result, test in pairs:
        if result.status not in _SCORED_STATUSES:
            continue
        w = severity_weight(test["severity"], cfg)
        total_w += w
        total_pts += status_points(result.status, cfg) * w
    if total_w == 0:
        return 0.0
    return 100.0 * total_pts / total_w


def maturity_level(score: float, cfg: dict) -> int:
    # Sort ascending by max so the first band whose ceiling the score falls at or under wins.
    # This handles fractional scores that sit between integer band boundaries.
    for band in sorted(cfg["maturity_bands"], key=lambda b: b["max"]):
        if score <= band["max"]:
            return band["level"]
    return cfg["maturity_bands"][-1]["level"]


def rag_status(score: float, has_critical_fail: bool, cfg: dict) -> RAGStatus:
    if has_critical_fail or score < cfg["rag_bands"]["amber"]:
        return RAGStatus.red
    if score < cfg["rag_bands"]["green"]:
        return RAGStatus.amber
    return RAGStatus.green


def _has_critical_fail(pairs: list[tuple[TestResult, dict]]) -> bool:
    return any(
        r.status in (TestStatus.fail, TestStatus.error) and t.get("severity") == "critical"
        for r, t in pairs
    )


def _has_scored_results(pairs: list[tuple[TestResult, dict]]) -> bool:
    return any(r.status in _SCORED_STATUSES for r, _ in pairs)


def aegis_index(pillar_scores: list[tuple[str, float]], pillar_weights: dict[str, float]) -> float:
    """Weighted average of per-pillar scores."""
    total_w = sum(pillar_weights.get(p, 1.0) for p, _ in pillar_scores)
    if total_w == 0:
        return 0.0
    return sum(s * pillar_weights.get(p, 1.0) for p, s in pillar_scores) / total_w


def compute_scores(run_id: str, session: Session) -> list[Score]:
    """Compute and persist all Score rows for a given run."""
    cfg = load_config()
    tests = load_test_library(_TESTLIB_DIR)
    test_map: dict[str, dict] = {t["id"]: t for t in tests}
    pillar_weights: dict[str, float] = cfg.get("pillar_weights", {})

    results = session.exec(select(TestResult).where(TestResult.run_id == run_id)).all()
    systems = session.exec(select(AISystem)).all()
    system_map = {s.id: s for s in systems}

    # Group results: system_id → pillar → [(result, test)]
    by_system: dict[str, list[TestResult]] = {}
    for r in results:
        by_system.setdefault(r.system_id, []).append(r)

    scores: list[Score] = []
    # system_id → (aegis_index_value, risk_multiplier)
    system_index: dict[str, tuple[float, float]] = {}
    # bu_name → list of system_ids
    bu_map: dict[str, list[str]] = {}

    for system_id, sys_results in by_system.items():
        system = system_map.get(system_id)
        if not system:
            continue

        risk_mult = cfg["risk_tier_multipliers"].get(system.risk_tier.value, 1.0)
        bu_map.setdefault(system.business_unit, []).append(system_id)

        # Group by pillar
        by_pillar: dict[str, list[tuple[TestResult, dict]]] = {}
        for r in sys_results:
            test = test_map.get(r.test_id)
            if not test:
                continue
            by_pillar.setdefault(test["pillar"], []).append((r, test))

        all_pairs = [(r, test_map[r.test_id]) for r in sys_results if r.test_id in test_map]
        system_critical_fail = _has_critical_fail(all_pairs)

        per_pillar: list[tuple[str, float]] = []
        for pillar, pairs in by_pillar.items():
            if not _has_scored_results(pairs):
                continue  # all na/pending — exclude from index and table
            ps = pillar_score(pairs, cfg)
            pillar_crit = _has_critical_fail(pairs)
            rag = rag_status(ps, pillar_crit, cfg)
            mat = maturity_level(ps, cfg)

            sc = Score(
                run_id=run_id,
                scope="system",
                scope_id=system_id,
                pillar=pillar,
                score=round(ps, 2),
                maturity=mat,
                rag=rag,
            )
            session.add(sc)
            scores.append(sc)
            per_pillar.append((pillar, ps))

        ai = aegis_index(per_pillar, pillar_weights)
        rag = rag_status(ai, system_critical_fail, cfg)
        mat = maturity_level(ai, cfg)

        overall = Score(
            run_id=run_id,
            scope="system",
            scope_id=system_id,
            pillar="overall",
            score=round(ai, 2),
            maturity=mat,
            rag=rag,
        )
        session.add(overall)
        scores.append(overall)
        system_index[system_id] = (ai, risk_mult)

    # BU roll-up
    for bu, sys_ids in bu_map.items():
        entries = [system_index[sid] for sid in sys_ids if sid in system_index]
        if not entries:
            continue
        total_w = sum(rm for _, rm in entries)
        bu_idx = sum(idx * rm for idx, rm in entries) / total_w if total_w else 0.0
        bu_pairs = [
            (r, test_map[r.test_id])
            for sid in sys_ids
            for r in by_system.get(sid, [])
            if r.test_id in test_map
        ]
        bu_crit = _has_critical_fail(bu_pairs)
        rag = rag_status(bu_idx, bu_crit, cfg)
        mat = maturity_level(bu_idx, cfg)

        bu_score = Score(
            run_id=run_id,
            scope="bu",
            scope_id=bu,
            pillar="overall",
            score=round(bu_idx, 2),
            maturity=mat,
            rag=rag,
        )
        session.add(bu_score)
        scores.append(bu_score)

    # Org roll-up
    all_entries = list(system_index.values())
    if all_entries:
        total_w = sum(rm for _, rm in all_entries)
        org_idx = sum(idx * rm for idx, rm in all_entries) / total_w if total_w else 0.0
        org_pairs = [(r, test_map[r.test_id]) for r in results if r.test_id in test_map]
        org_crit = _has_critical_fail(org_pairs)
        rag = rag_status(org_idx, org_crit, cfg)
        mat = maturity_level(org_idx, cfg)

        org_score = Score(
            run_id=run_id,
            scope="org",
            scope_id="org",
            pillar="overall",
            score=round(org_idx, 2),
            maturity=mat,
            rag=rag,
        )
        session.add(org_score)
        scores.append(org_score)

    session.commit()
    return scores
