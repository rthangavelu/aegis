# Test Library

This document covers the YAML test case schema, applies_to matching rules, the full list of 41 test cases, technical checks reference, and how to add new tests and metrics.

---

## YAML schema

Each test case lives at `aegis/testlib/<pillar>/<ID>.yaml`.

```yaml
id: FAIR-001                          # Unique identifier (required)
name: Disparate impact ratio          # Short human-readable name (required)
pillar: Fairness                      # One of the 9 pillars (required)
type: technical                       # technical | evidence | process | attestation (required)
severity: critical                    # critical | high | medium | low (required)
version: 1                            # Schema version, always 1 (required)
owner_role: ML Lead                   # Who is accountable for this test (required)

applies_to:                           # Selector — test only runs when these match
  risk_tier: [high, unacceptable]     # Optional: list of matching risk tiers
  model_type: [classification]        # Optional: list of matching model types
  lifecycle_stage: [production]       # Optional: list of matching lifecycle stages

mappings:                             # Regulatory references
  - framework: NIST_AI_RMF
    ref: "MEASURE 2.11"
  - framework: EU_AI_ACT
    ref: "Art. 10(2)"

inputs:                               # Inputs to the runner (type-specific)
  dataset: "${system.eval_dataset}"   # Path to CSV eval dataset
  protected_attributes: [gender]      # Columns to test for fairness

check:                                # For technical tests
  metric: disparate_impact_ratio      # Name of function in engine/checks/
  aggregate: min                      # How to reduce multi-group result
  threshold:
    pass: ">= 0.9"                    # Pass criterion
    warn: ">= 0.8"                    # Warn criterion (fail if below)

document:                             # For evidence tests
  path: "${system.data_sources[0]}/dpa.pdf"
  max_age_days: 365
  required_sections:
    - "Data Retention"
    - "Data Subject Rights"

remediation_id: REM-FAIR-001          # Optional: linked remediation playbook
```

---

## applies_to matching

The `selector.py` module matches a test's `applies_to` block against system fields before execution. If a field is omitted from `applies_to`, it matches all values.

| applies_to field | System field | Match condition |
|---|---|---|
| `risk_tier` | `AISystem.risk_tier` | system value in the list |
| `model_type` | `AISystem.model_type` | system value in the list |
| `lifecycle_stage` | `AISystem.lifecycle_stage` | system value in the list |

Tests that do not match get status `na` and are excluded from scoring.

---

## All 41 test cases

### Governance & Accountability

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| GOV-001 | Deployment approval ticket | process | high | NIST AI RMF GOVERN 1.1 |
| GOV-002 | Model card present and complete | evidence | high | ISO/IEC 42001 Annex A.6.2 |
| GOV-003 | Model change log maintained | evidence | medium | NIST AI RMF GOVERN 6.1 |
| GOV-004 | Model risk framework documented | evidence | high | ISO/IEC 42001 Clause 6.1 |
| GOV-005 | Third-party supply chain AI risk | evidence | high | EU AI Act Arts. 25-28 |

### Fairness

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| FAIR-001 | Disparate impact ratio (four-fifths rule) | technical | critical | EU AI Act Art. 10(2), NIST MEASURE 2.11 |
| FAIR-002 | Equal opportunity difference | technical | high | NIST AI RMF MEASURE 2.11 |
| FAIR-003 | False positive rate parity | technical | high | EU AI Act Art. 10(2) |
| FAIR-004 | Predictive parity / calibration | technical | high | NIST AI RMF MEASURE 2.11 |

### Transparency

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| TRAN-001 | Transparency report published | evidence | high | EU AI Act Art. 13 |
| TRAN-002 | Model card maps to system | evidence | medium | ISO/IEC 42001 Annex A.6.2 |
| TRAN-003 | Known limitations documented | evidence | medium | NIST AI RMF MAP 1.6 |
| TRAN-004 | Explainability method documented | evidence | high | EU AI Act Art. 13 |

### Privacy & Data

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| PRIV-001 | Data protection agreement in place | evidence | critical | GDPR Art. 28 |
| PRIV-002 | Training data policy documented | evidence | high | EU AI Act Art. 10(3) |
| PRIV-003 | PII leak rate below threshold | technical | high | GDPR Art. 5(1)(f) |
| PRIV-004 | Training data provenance and lineage | evidence | high | EU AI Act Art. 10(3) |
| PRIV-005 | Lawful basis / consent for training data | evidence | high | GDPR Art. 6 |
| PRIV-006 | Right to erasure process documented | evidence | medium | GDPR Art. 17 |

### Safety & Security

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| SAFE-001 | Pre-deployment risk assessment | evidence | critical | EU AI Act Art. 9 |
| SAFE-002 | Adversarial / red-team testing | evidence | high | NIST AI RMF MEASURE 2.6 |
| SAFE-003 | Security incident log maintained | process | high | EU AI Act Art. 17 |
| SAFE-004 | Post-market surveillance + incident reporting | evidence | high | EU AI Act Arts. 72-74 |

### Reliability

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| REL-001 | Accuracy floor met | technical | critical | NIST AI RMF MEASURE 2.5 |
| REL-002 | Monitoring dashboard in place | evidence | high | NIST AI RMF MANAGE 4.1 |
| REL-003 | Latency SLA documented | evidence | medium | ISO/IEC 42001 Clause 9.1 |
| REL-004 | Input data drift detection | technical | critical | NIST AI RMF MANAGE 4.1 |

### Human Oversight

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| HUM-001 | Human override log maintained | process | high | EU AI Act Art. 14 |
| HUM-002 | Human review attestation | attestation | high | EU AI Act Art. 14 |
| HUM-003 | Escalation policy documented | evidence | medium | NIST AI RMF GOVERN 6.2 |
| HUM-004 | Algorithmic recourse / appeal process | evidence | critical | EU AI Act Art. 14 |

### GenAI-specific

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| GENAI-001 | Jailbreak rate below threshold | technical | critical | EU AI Act Art. 15 |
| GENAI-002 | Hallucination controls in place | evidence | high | NIST AI RMF MEASURE 2.6 |
| GENAI-003 | Output filtering documented | evidence | high | EU AI Act Art. 15 |
| GENAI-004 | Acceptable use policy published | evidence | medium | EU AI Act Art. 13 |
| GENAI-005 | GenAI incident reporting process | process | high | EU AI Act Art. 72 |
| GENAI-006 | AI-generated content provenance | evidence | medium | EU AI Act Art. 50 |
| GENAI-007 | GPAI copyright policy + training data summary | evidence | high | EU AI Act Art. 53 |

### Training & Culture

| ID | Name | Type | Severity | Regulatory ref |
|---|---|---|---|---|
| CULT-001 | AI ethics training completion | attestation | medium | ISO/IEC 42001 Clause 7.2 |
| CULT-002 | AI policy acknowledgment | attestation | medium | ISO/IEC 42001 Clause 7.3 |
| CULT-003 | Bias awareness training completed | attestation | medium | NIST AI RMF GOVERN 4.2 |

---

## Technical checks

Technical checks live in `aegis/engine/checks/`. Each is a function accepting a `pd.DataFrame` (and optional config) returning a `float`.

| Check | Measures | Library | Used by |
|---|---|---|---|
| `disparate_impact_ratio` | Selection rate ratio between groups (four-fifths rule: fail < 0.8) | fairlearn | FAIR-001 |
| `equal_opportunity_difference` | True positive rate difference between groups | fairlearn | FAIR-002 |
| `accuracy_floor` | Overall classification accuracy | scikit-learn | REL-001 |
| `jailbreak_rate` | Fraction of jailbreak prompts that succeed (mock in v0.1) | — | GENAI-001 |
| `pii_leak_rate` | Fraction of outputs containing PII patterns (mock in v0.1) | — | PRIV-003 |
| `drift` | Statistical divergence of input distribution vs. baseline | scipy | REL-004 |
| `predictive_parity` | Positive predictive value difference across groups | scikit-learn | FAIR-004 |

---

## How to add a test case

1. Choose the pillar and assign the next available ID (e.g. `FAIR-005`).
2. Create `aegis/testlib/<pillar>/<ID>.yaml` using the schema above.
3. Run `uv run aegis validate` — it will fail loudly if the schema is invalid.
4. Run `uv run aegis run --all` and confirm the new test appears in results.
5. Write at least one test in `tests/` covering the new test case's runner path.

---

## How to add a technical metric

1. Create `aegis/engine/checks/<metric_name>.py`:

```python
import pandas as pd

def <metric_name>(df: pd.DataFrame, protected_col: str, label_col: str) -> float:
    """Return a float; higher = better."""
    ...
```

2. Register it in `aegis/engine/runners/technical.py` under `_SCALAR_CHECKS`:

```python
_SCALAR_CHECKS = {
    "disparate_impact_ratio": disparate_impact_ratio,
    "my_new_metric": my_new_metric,   # add here
    ...
}
```

3. Write tests in `tests/test_checks.py` covering pass, warn, fail and edge cases (empty df, single group, NaN values).

4. Create a YAML test case that uses the new metric under `check.metric`.
