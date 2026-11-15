"""Inventory CRUD — read and write AI systems to SQLite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from aegis.db import get_session, init_db
from aegis.engine.loader import load_systems
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier

_SEED_FILE = Path(__file__).parent.parent / "seed" / "systems.yaml"


def _system_from_dict(d: dict) -> AISystem:
    return AISystem(
        id=d["id"],
        name=d["name"],
        owner=d["owner"],
        business_unit=d["business_unit"],
        purpose=d["purpose"],
        model_type=ModelType(d["model_type"]),
        risk_tier=RiskTier(d["risk_tier"]),
        lifecycle_stage=LifecycleStage(d["lifecycle_stage"]),
        endpoint=d.get("endpoint"),
        eval_dataset=d.get("eval_dataset"),
        data_sources=json.dumps(d.get("data_sources", [])),
        jurisdictions=json.dumps(d.get("jurisdictions", [])),
        mock=d.get("mock", True),
    )


def seed_inventory(session: Optional[Session] = None) -> int:
    """Load seed systems into the database. Returns count inserted."""
    init_db()
    systems_data = load_systems(_SEED_FILE)
    if session is None:
        session = get_session()
    inserted = 0
    with session:
        for d in systems_data:
            existing = session.get(AISystem, d["id"])
            if existing is None:
                session.add(_system_from_dict(d))
                inserted += 1
        session.commit()
    return inserted


def list_systems(session: Optional[Session] = None) -> list[AISystem]:
    if session is None:
        session = get_session()
    with session:
        return session.exec(select(AISystem)).all()


def get_system(system_id: str, session: Optional[Session] = None) -> Optional[AISystem]:
    if session is None:
        session = get_session()
    with session:
        return session.get(AISystem, system_id)


def upsert_system(system: AISystem, session: Optional[Session] = None) -> None:
    if session is None:
        session = get_session()
    with session:
        session.merge(system)
        session.commit()


def delete_system(system_id: str, session: Optional[Session] = None) -> bool:
    if session is None:
        session = get_session()
    with session:
        obj = session.get(AISystem, system_id)
        if obj is None:
            return False
        session.delete(obj)
        session.commit()
        return True
