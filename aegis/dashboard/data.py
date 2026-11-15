"""Data loading layer for the Aegis dashboard. All DB access lives here."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlmodel import select

from aegis.db import get_session, init_db
from aegis.engine.loader import load_test_library
from aegis.models import AISystem, Score, TestResult, TestRun
from aegis.recommend.engine import build_recommendations
from aegis.scoring.engine import compute_scores

_PKG = Path(__file__).parent.parent
_TESTLIB_DIR = _PKG / "testlib"
_REMEDIATION_DIR = _PKG / "remediation"


def latest_run_id() -> str | None:
    init_db()
    with get_session() as session:
        runs = session.exec(select(TestRun).order_by(TestRun.started_at.desc())).all()
        return runs[0].id if runs else None


def ensure_scored(run_id: str) -> None:
    """Compute and store scores if not already present for this run."""
    with get_session() as session:
        existing = session.exec(
            select(Score).where(Score.run_id == run_id, Score.pillar == "overall")
        ).all()
        if not existing:
            compute_scores(run_id, session)


@st.cache_data(ttl=30, show_spinner=False)
def load_systems() -> list[dict]:
    with get_session() as session:
        systems = session.exec(select(AISystem)).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "owner": s.owner,
                "business_unit": s.business_unit,
                "purpose": s.purpose,
                "model_type": s.model_type.value,
                "risk_tier": s.risk_tier.value,
                "lifecycle_stage": s.lifecycle_stage.value,
                "mock": s.mock,
            }
            for s in systems
        ]


@st.cache_data(ttl=30, show_spinner=False)
def load_scores(run_id: str) -> list[dict]:
    with get_session() as session:
        scores = session.exec(select(Score).where(Score.run_id == run_id)).all()
        return [
            {
                "scope": s.scope,
                "scope_id": s.scope_id,
                "pillar": s.pillar,
                "score": s.score,
                "maturity": s.maturity,
                "rag": s.rag.value,
            }
            for s in scores
        ]


@st.cache_data(ttl=30, show_spinner=False)
def load_results(run_id: str) -> list[dict]:
    with get_session() as session:
        results = session.exec(select(TestResult).where(TestResult.run_id == run_id)).all()
        return [
            {
                "system_id": r.system_id,
                "test_id": r.test_id,
                "status": r.status.value,
                "metric_value": r.metric_value,
                "threshold": r.threshold or "",
                "message": r.message or "",
                "evidence_uri": r.evidence_uri or "",
                "evidence_hash": r.evidence_hash or "",
            }
            for r in results
        ]


@st.cache_data(ttl=300, show_spinner=False)
def load_tests() -> list[dict]:
    return load_test_library(_TESTLIB_DIR)


@st.cache_data(ttl=30, show_spinner=False)
def load_recommendations(run_id: str) -> list[dict]:
    with get_session() as session:
        items = build_recommendations(run_id, session)
    return [
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
            "priority": r.priority,
            "projected_uplift": r.projected_uplift,
            "current_scores": r.current_scores,
            "projected_scores": r.projected_scores,
            "steps": r.steps,
        }
        for r in items
    ]
