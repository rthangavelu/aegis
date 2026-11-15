"""Test selector — matches a test's applies_to block against an AISystem."""

from __future__ import annotations

from aegis.models import AISystem


def applies_to(test: dict, system: AISystem) -> bool:
    criteria = test.get("applies_to", {})
    if not criteria:
        return True
    if "risk_tier" in criteria and system.risk_tier.value not in criteria["risk_tier"]:
        return False
    if "model_type" in criteria and system.model_type.value not in criteria["model_type"]:
        return False
    if (
        "lifecycle_stage" in criteria
        and system.lifecycle_stage.value not in criteria["lifecycle_stage"]
    ):
        return False
    return True
