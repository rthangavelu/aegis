"""Pydantic + SQLModel data models for Aegis."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel

NaiveDT = Annotated[datetime, NaiveDatetime]


class ModelType(str, Enum):
    classification = "classification"
    regression = "regression"
    llm = "llm"
    recommender = "recommender"
    other = "other"


class RiskTier(str, Enum):
    unacceptable = "unacceptable"
    high = "high"
    limited = "limited"
    minimal = "minimal"


class LifecycleStage(str, Enum):
    development = "development"
    testing = "testing"
    production = "production"
    deprecated = "deprecated"


class AISystem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    owner: str
    business_unit: str
    purpose: str
    model_type: ModelType
    risk_tier: RiskTier
    lifecycle_stage: LifecycleStage
    endpoint: Optional[str] = None
    eval_dataset: Optional[str] = None
    data_sources: str = Field(default="[]")  # JSON-encoded list[str]
    jurisdictions: str = Field(default="[]")  # JSON-encoded list[str]
    mock: bool = True

    def get_data_sources(self) -> list[str]:
        return json.loads(self.data_sources)

    def get_jurisdictions(self) -> list[str]:
        return json.loads(self.jurisdictions)


class Trigger(str, Enum):
    manual = "manual"
    schedule = "schedule"
    ci = "ci"


class TestRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    started_at: NaiveDT
    finished_at: Optional[NaiveDT] = None
    trigger: Trigger = Trigger.manual
    scope: str = "all"


class TestStatus(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    na = "na"
    pending = "pending"
    error = "error"


class TestResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str
    system_id: str
    test_id: str
    status: TestStatus
    metric_value: Optional[float] = None
    threshold: Optional[str] = None
    evidence_uri: Optional[str] = None
    evidence_hash: Optional[str] = None
    message: Optional[str] = None
    executed_at: NaiveDT


class RAGStatus(str, Enum):
    green = "Green"
    amber = "Amber"
    red = "Red"


class Score(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str
    scope: str  # system | bu | org
    scope_id: str
    pillar: str
    score: float
    maturity: int
    rag: RAGStatus


class Tier(str, Enum):
    p0 = "P0"
    quick_win = "quick_win"
    strategic = "strategic"
    hygiene = "hygiene"


class Effort(str, Enum):
    s = "S"
    m = "M"
    large = "L"


class RecommendationStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Recommendation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    test_id: str
    system_ids: str = "[]"  # JSON list
    priority: float
    tier: Tier
    effort: Effort
    owner_role: str
    projected_uplift: float
    verify_test_id: str
    status: RecommendationStatus = RecommendationStatus.open
