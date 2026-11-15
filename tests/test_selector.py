"""Tests for aegis.engine.selector.applies_to."""

from aegis.engine.selector import applies_to
from aegis.models import AISystem, LifecycleStage, ModelType, RiskTier


def _system(**kwargs) -> AISystem:
    defaults = dict(
        id="test-sys",
        name="Test System",
        owner="owner@example.com",
        business_unit="BU",
        purpose="Testing",
        model_type=ModelType.classification,
        risk_tier=RiskTier.high,
        lifecycle_stage=LifecycleStage.production,
    )
    defaults.update(kwargs)
    return AISystem(**defaults)


def _test(applies_to_block: dict) -> dict:
    return {"id": "TST-001", "applies_to": applies_to_block}


def test_empty_applies_to_matches_all():
    sys = _system(risk_tier=RiskTier.minimal, model_type=ModelType.llm)
    assert applies_to(_test({}), sys) is True


def test_risk_tier_match():
    sys = _system(risk_tier=RiskTier.high)
    assert applies_to(_test({"risk_tier": ["high"]}), sys) is True


def test_risk_tier_no_match():
    sys = _system(risk_tier=RiskTier.minimal)
    assert applies_to(_test({"risk_tier": ["high"]}), sys) is False


def test_model_type_match():
    sys = _system(model_type=ModelType.llm)
    assert applies_to(_test({"model_type": ["llm"]}), sys) is True


def test_model_type_no_match():
    sys = _system(model_type=ModelType.classification)
    assert applies_to(_test({"model_type": ["llm"]}), sys) is False


def test_lifecycle_stage_match():
    sys = _system(lifecycle_stage=LifecycleStage.production)
    assert applies_to(_test({"lifecycle_stage": ["production"]}), sys) is True


def test_lifecycle_stage_no_match():
    sys = _system(lifecycle_stage=LifecycleStage.development)
    assert applies_to(_test({"lifecycle_stage": ["production"]}), sys) is False


def test_multiple_criteria_all_match():
    sys = _system(risk_tier=RiskTier.high, model_type=ModelType.classification)
    assert applies_to(_test({"risk_tier": ["high"], "model_type": ["classification"]}), sys) is True


def test_multiple_criteria_one_miss():
    sys = _system(risk_tier=RiskTier.limited, model_type=ModelType.classification)
    assert (
        applies_to(_test({"risk_tier": ["high"], "model_type": ["classification"]}), sys) is False
    )


def test_multi_value_list_match():
    sys = _system(risk_tier=RiskTier.limited)
    assert applies_to(_test({"risk_tier": ["high", "limited"]}), sys) is True
