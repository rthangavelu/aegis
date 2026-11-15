"""Aegis MCP server — exposes Aegis tools via the Model Context Protocol (stdio)."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from sqlmodel import select

from aegis.db import get_session, init_db
from aegis.engine.executor import execute_run
from aegis.engine.loader import load_test_library
from aegis.inventory.store import list_systems as _list_systems
from aegis.inventory.store import seed_inventory, upsert_system
from aegis.models import (
    AISystem,
    LifecycleStage,
    ModelType,
    RiskTier,
    Score,
    TestResult,
    TestRun,
    TestStatus,
)
from aegis.recommend.engine import build_recommendations
from aegis.scoring.engine import compute_scores

_PKG = Path(__file__).parent
_TESTLIB_DIR = _PKG / "testlib"

server = MCPServer(
    name="aegis",
    title="Aegis AI Governance",
    description=(
        "AI governance and ethics testing agent. "
        "Run assessments against AI systems, compute Aegis Index scores (0–100), "
        "and get prioritised recommendations covering fairness, transparency, "
        "privacy, safety, reliability, human oversight, GenAI risks, and governance. "
        "Covers NIST AI RMF, ISO/IEC 42001, and EU AI Act."
    ),
)


def _latest_run_id() -> str | None:
    with get_session() as session:
        runs = session.exec(select(TestRun).order_by(TestRun.started_at.desc())).all()
        return runs[0].id if runs else None


def _ensure_scored(run_id: str) -> None:
    with get_session() as session:
        existing = session.exec(
            select(Score).where(Score.run_id == run_id, Score.pillar == "overall")
        ).all()
        if not existing:
            compute_scores(run_id, session)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@server.tool()
def list_systems() -> str:
    """List all AI systems in the Aegis inventory with risk tier, model type, owner, and business unit."""
    init_db()
    systems = _list_systems()
    if not systems:
        return "No systems found. Run run_assessment or seed_systems first."
    rows = [
        {
            "id": s.id,
            "name": s.name,
            "risk_tier": s.risk_tier.value,
            "model_type": s.model_type.value,
            "lifecycle_stage": s.lifecycle_stage.value,
            "owner": s.owner,
            "business_unit": s.business_unit,
            "mock": s.mock,
        }
        for s in systems
    ]
    return json.dumps(rows, indent=2)


@server.tool()
def seed_systems() -> str:
    """Seed the three mock AI systems (credit-scoring-v3, support-chatbot, resume-screener) into the inventory. Safe to call multiple times."""
    init_db()
    n = seed_inventory()
    if n:
        return f"Seeded {n} mock AI system(s) into the inventory."
    return "Systems already present — nothing to seed."


@server.tool()
def run_assessment(system_id: str = "") -> str:
    """
    Run a full governance assessment: seed systems if needed, execute all test cases,
    compute Aegis Index scores, and return a summary with RAG status per system.
    Leave system_id empty to assess all systems.
    """
    init_db()
    seed_inventory()
    tests = load_test_library(_TESTLIB_DIR)
    systems = _list_systems()
    if system_id:
        systems = [s for s in systems if s.id == system_id]
        if not systems:
            return f"System '{system_id}' not found. Use list_systems to see available IDs."

    with get_session() as session:
        run = execute_run(systems, tests, session)
        run_id = run.id
        results = session.exec(select(TestResult).where(TestResult.run_id == run_id)).all()
        results = list(results)

    _ensure_scored(run_id)

    with get_session() as session:
        scores = session.exec(
            select(Score).where(
                Score.run_id == run_id,
                Score.pillar == "overall",
            )
        ).all()
        summary = []
        for sc in sorted(scores, key=lambda s: -s.score):
            sys_results = [r for r in results if r.system_id == sc.scope_id]
            fail_count = sum(1 for r in sys_results if r.status == TestStatus.fail)
            warn_count = sum(1 for r in sys_results if r.status == TestStatus.warn)
            summary.append(
                {
                    "system_id": sc.scope_id,
                    "aegis_index": round(sc.score, 1),
                    "rag": sc.rag.value,
                    "maturity": sc.maturity,
                    "fail": fail_count,
                    "warn": warn_count,
                }
            )
        org = session.exec(
            select(Score).where(
                Score.run_id == run_id,
                Score.scope == "org",
                Score.pillar == "overall",
            )
        ).first()
        org_summary = (
            {"aegis_index": round(org.score, 1), "rag": org.rag.value, "maturity": org.maturity}
            if org
            else {}
        )

    return json.dumps({"run_id": run_id, "systems": summary, "organisation": org_summary}, indent=2)


@server.tool()
def get_scores(system_id: str = "", run_id: str = "") -> str:
    """
    Get Aegis Index scores. Optionally filter by system_id or specify a run_id.
    Returns overall scores and per-pillar breakdown. Leave both empty for the latest run.
    """
    init_db()
    if not run_id:
        run_id = _latest_run_id() or ""
    if not run_id:
        return "No test runs found. Call run_assessment first."
    _ensure_scored(run_id)

    with get_session() as session:
        query = select(Score).where(Score.run_id == run_id)
        scores = session.exec(query).all()

    rows = [
        {
            "scope": s.scope,
            "scope_id": s.scope_id,
            "pillar": s.pillar,
            "score": round(s.score, 1),
            "maturity": s.maturity,
            "rag": s.rag.value,
        }
        for s in scores
        if not system_id or s.scope_id == system_id or s.scope in ("org", "bu")
    ]
    return json.dumps(rows, indent=2)


@server.tool()
def get_test_results(system_id: str, status_filter: str = "", run_id: str = "") -> str:
    """
    Get test results for an AI system. system_id is required (use list_systems to see IDs).
    status_filter: comma-separated statuses to include (pass, warn, fail, na, pending, error).
    Leave empty to return all statuses. Leave run_id empty for the latest run.
    """
    init_db()
    if not run_id:
        run_id = _latest_run_id() or ""
    if not run_id:
        return "No test runs found. Call run_assessment first."

    statuses = [s.strip() for s in status_filter.split(",") if s.strip()] if status_filter else []
    tests = load_test_library(_TESTLIB_DIR)
    test_meta = {t["id"]: t for t in tests}

    with get_session() as session:
        results = session.exec(
            select(TestResult).where(TestResult.run_id == run_id, TestResult.system_id == system_id)
        ).all()

    rows = []
    for r in sorted(results, key=lambda x: x.test_id):
        if statuses and r.status.value not in statuses:
            continue
        t = test_meta.get(r.test_id, {})
        rows.append(
            {
                "test_id": r.test_id,
                "name": t.get("name", ""),
                "pillar": t.get("pillar", ""),
                "type": t.get("type", ""),
                "severity": t.get("severity", ""),
                "status": r.status.value,
                "metric_value": r.metric_value,
                "threshold": r.threshold,
                "message": r.message or "",
                "evidence_uri": r.evidence_uri or "",
            }
        )
    return json.dumps(rows, indent=2)


@server.tool()
def get_failing_tests(system_id: str = "", severity: str = "", run_id: str = "") -> str:
    """
    Get all failing tests (status: fail or error), optionally filtered by system_id
    and/or severity (critical, high, medium, low). Leave run_id empty for the latest run.
    Results are sorted by severity then system.
    """
    init_db()
    if not run_id:
        run_id = _latest_run_id() or ""
    if not run_id:
        return "No test runs found. Call run_assessment first."

    tests = load_test_library(_TESTLIB_DIR)
    test_meta = {t["id"]: t for t in tests}
    _SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    with get_session() as session:
        query = select(TestResult).where(
            TestResult.run_id == run_id,
            TestResult.status.in_([TestStatus.fail, TestStatus.error]),
        )
        results = session.exec(query).all()

    rows = []
    for r in results:
        if system_id and r.system_id != system_id:
            continue
        t = test_meta.get(r.test_id, {})
        if severity and t.get("severity") != severity:
            continue
        rows.append(
            {
                "system_id": r.system_id,
                "test_id": r.test_id,
                "name": t.get("name", ""),
                "pillar": t.get("pillar", ""),
                "severity": t.get("severity", ""),
                "status": r.status.value,
                "message": r.message or "",
                "metric_value": r.metric_value,
            }
        )
    rows.sort(key=lambda x: (_SEV_ORDER.get(x["severity"], 9), x["system_id"]))
    return json.dumps(rows, indent=2)


@server.tool()
def get_pillar_breakdown(system_id: str, run_id: str = "") -> str:
    """
    Get the Aegis Index broken down by pillar for a specific AI system.
    Shows score, maturity level, and RAG status per pillar plus the overall index.
    Leave run_id empty for the latest run.
    """
    init_db()
    if not run_id:
        run_id = _latest_run_id() or ""
    if not run_id:
        return "No test runs found. Call run_assessment first."
    _ensure_scored(run_id)

    with get_session() as session:
        scores = session.exec(
            select(Score).where(
                Score.run_id == run_id,
                Score.scope == "system",
                Score.scope_id == system_id,
            )
        ).all()

    if not scores:
        return f"No scores found for system '{system_id}' in run '{run_id}'."

    overall = next((s for s in scores if s.pillar == "overall"), None)
    pillars = sorted([s for s in scores if s.pillar != "overall"], key=lambda s: s.score)
    result = {
        "system_id": system_id,
        "overall": {
            "score": round(overall.score, 1),
            "maturity": overall.maturity,
            "rag": overall.rag.value,
        }
        if overall
        else {},
        "pillars": [
            {
                "pillar": s.pillar,
                "score": round(s.score, 1),
                "maturity": s.maturity,
                "rag": s.rag.value,
            }
            for s in pillars
        ],
    }
    return json.dumps(result, indent=2)


@server.tool()
def get_recommendations(run_id: str = "") -> str:
    """
    Get a prioritised improvement plan for the latest (or specified) test run.
    Returns recommendations grouped by tier: P0 (critical, fix immediately),
    quick_win, strategic, and hygiene. Each recommendation includes projected
    score uplift, affected systems, effort estimate, and remediation steps.
    """
    init_db()
    if not run_id:
        run_id = _latest_run_id() or ""
    if not run_id:
        return "No test runs found. Call run_assessment first."
    _ensure_scored(run_id)

    with get_session() as session:
        items = build_recommendations(run_id, session)

    if not items:
        return "No recommendations — no failing tests found."

    result = []
    for r in items:
        result.append(
            {
                "tier": r.tier,
                "title": r.title,
                "test_id": r.test_id,
                "pillar": r.pillar,
                "severity": r.severity,
                "effort": r.effort,
                "owner_role": r.owner_role,
                "org_wide_fix": r.org_wide_fix,
                "systems_affected": r.systems_affected,
                "priority_score": r.priority,
                "projected_uplift_pts": r.projected_uplift,
                "steps": r.steps,
            }
        )
    return json.dumps(result, indent=2)


@server.tool()
def add_system(
    id: str,
    name: str,
    owner: str,
    business_unit: str,
    purpose: str,
    model_type: str,
    risk_tier: str,
    lifecycle_stage: str = "production",
    eval_dataset: str = "",
) -> str:
    """
    Add a new AI system to the inventory.
    model_type: classification | regression | llm | recommender | other
    risk_tier: unacceptable | high | limited | minimal
    lifecycle_stage: development | testing | production | deprecated
    eval_dataset: path to a CSV evaluation dataset (optional).
    """
    init_db()
    try:
        system = AISystem(
            id=id,
            name=name,
            owner=owner,
            business_unit=business_unit,
            purpose=purpose,
            model_type=ModelType(model_type),
            risk_tier=RiskTier(risk_tier),
            lifecycle_stage=LifecycleStage(lifecycle_stage),
            eval_dataset=eval_dataset or None,
            mock=False,
        )
    except ValueError as e:
        return f"Invalid value: {e}. Check model_type, risk_tier and lifecycle_stage."
    upsert_system(system)
    return f"System '{id}' added to inventory. Run run_assessment to assess it."


@server.tool()
def validate_library() -> str:
    """Validate all test cases and remediations against their schemas. Returns pass/fail summary."""
    from aegis.engine.loader import load_remediations

    _REMEDIATION_DIR = _PKG / "remediation"
    errors = []
    try:
        tests = load_test_library(_TESTLIB_DIR)
        test_msg = f"{len(tests)} test case(s) valid"
    except Exception as e:
        errors.append(str(e))
        test_msg = f"test library error: {e}"

    try:
        remediations = load_remediations(_REMEDIATION_DIR)
        rem_msg = f"{len(remediations)} remediation(s) valid"
    except Exception as e:
        errors.append(str(e))
        rem_msg = f"remediations error: {e}"

    status = "PASS" if not errors else "FAIL"
    return json.dumps({"status": status, "tests": test_msg, "remediations": rem_msg}, indent=2)
