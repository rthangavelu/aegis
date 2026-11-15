"""Tests for SQLModel data models."""

from __future__ import annotations

import os
from datetime import datetime

import pytest
from sqlmodel import Session, create_engine

from aegis.models import (
    AISystem,
    Effort,
    LifecycleStage,
    ModelType,
    RAGStatus,
    Recommendation,
    RecommendationStatus,
    RiskTier,
    Score,
    TestResult,
    TestRun,
    TestStatus,
    Tier,
    Trigger,
)


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["AEGIS_DB_PATH"] = str(db_path)
    from sqlmodel import SQLModel

    eng = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


class TestAISystemModel:
    def test_create_and_retrieve(self, session):
        system = AISystem(
            id="test-model",
            name="Test Model",
            owner="owner@example.com",
            business_unit="Engineering",
            purpose="Testing",
            model_type=ModelType.classification,
            risk_tier=RiskTier.high,
            lifecycle_stage=LifecycleStage.production,
            mock=True,
        )
        session.add(system)
        session.commit()

        result = session.get(AISystem, "test-model")
        assert result is not None
        assert result.name == "Test Model"
        assert result.risk_tier == RiskTier.high
        assert result.mock is True

    def test_enums_enforce_values(self):
        with pytest.raises(ValueError):
            ModelType("unknown_type")
        with pytest.raises(ValueError):
            RiskTier("ultra_high")


class TestTestRunModel:
    def test_create_test_run(self, session):
        run = TestRun(
            id="run-001",
            started_at=datetime(2026, 11, 1, 10, 0, 0),
            trigger=Trigger.manual,
            scope="all",
        )
        session.add(run)
        session.commit()

        result = session.get(TestRun, "run-001")
        assert result is not None
        assert result.trigger == Trigger.manual
        assert result.finished_at is None


class TestTestResultModel:
    def test_create_test_result(self, session):
        result = TestResult(
            run_id="run-001",
            system_id="resume-screener",
            test_id="FAIR-001",
            status=TestStatus.fail,
            metric_value=0.60,
            threshold=">= 0.8",
            message="Disparate impact ratio 0.60 below threshold 0.80",
            executed_at=datetime(2026, 11, 1, 10, 1, 0),
        )
        session.add(result)
        session.commit()

        from sqlmodel import select

        rows = session.exec(select(TestResult)).all()
        assert len(rows) == 1
        assert rows[0].status == TestStatus.fail
        assert rows[0].metric_value == pytest.approx(0.60)

    def test_error_status_exists(self):
        assert TestStatus.error.value == "error"

    def test_pass_status_value(self):
        assert TestStatus.pass_.value == "pass"


class TestScoreModel:
    def test_rag_enum_values(self):
        assert RAGStatus.green.value == "Green"
        assert RAGStatus.amber.value == "Amber"
        assert RAGStatus.red.value == "Red"

    def test_create_score(self, session):
        score = Score(
            run_id="run-001",
            scope="system",
            scope_id="resume-screener",
            pillar="Fairness",
            score=35.0,
            maturity=2,
            rag=RAGStatus.red,
        )
        session.add(score)
        session.commit()

        from sqlmodel import select

        rows = session.exec(select(Score)).all()
        assert rows[0].rag == RAGStatus.red


class TestRecommendationModel:
    def test_create_recommendation(self, session):
        rec = Recommendation(
            id="REC-001",
            test_id="FAIR-001",
            system_ids='["resume-screener"]',
            priority=18.0,
            tier=Tier.p0,
            effort=Effort.m,  # M = 1-4 weeks
            owner_role="ML Lead",
            projected_uplift=25.0,
            verify_test_id="FAIR-001",
            status=RecommendationStatus.open,
        )
        session.add(rec)
        session.commit()

        result = session.get(Recommendation, "REC-001")
        assert result.tier == Tier.p0
        assert result.effort == Effort.m
