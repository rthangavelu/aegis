# Contributing

This document covers how to extend Aegis: adding test cases, remediation playbooks, technical metrics, and new runner types. It also covers code conventions, the test suite, and linting.

---

## Adding a test case

### 1. Choose the pillar and ID

Pick the most appropriate pillar from the 9 available. Assign the next sequential ID within that pillar (e.g. if `FAIR-004` exists, create `FAIR-005`).

### 2. Create the YAML file

```
aegis/testlib/<pillar>/<ID>.yaml
```

Pillar directory names (use exactly as shown):

```
governance/   fairness/   transparency/   privacy/   safety/
reliability/  human_oversight/   genai/   culture/
```

### 3. Write the YAML

```yaml
id: FAIR-005
name: Intersectional disparate impact check
pillar: Fairness
type: technical                        # technical | evidence | process | attestation
severity: high                         # critical | high | medium | low
version: 1
owner_role: ML Lead

applies_to:
  risk_tier: [high, unacceptable]      # omit to match all
  model_type: [classification]         # omit to match all

mappings:
  - framework: NIST_AI_RMF
    ref: "MEASURE 2.11"
  - framework: EU_AI_ACT
    ref: "Art. 10(2)"

inputs:
  dataset: "${system.eval_dataset}"
  protected_attributes: [gender, age_band]

check:
  metric: disparate_impact_ratio       # must exist in engine/checks/
  aggregate: min
  threshold:
    pass: ">= 0.9"
    warn: ">= 0.8"

remediation_id: REM-FAIR-005           # optional — link to a playbook
```

For **evidence** tests, replace `inputs` and `check` with:

```yaml
document:
  path: "${system.data_sources[0]}/model_card.pdf"
  max_age_days: 365
  required_sections:
    - "Known Limitations"
    - "Bias and Fairness"
```

For **attestation** tests:

```yaml
attestation:
  question_id: "ethics-training-2026"
  expires_days: 365
```

### 4. Validate

```bash
uv run aegis validate
```

The loader validates against `schemas/test_case.json`. It will print the exact validation error if something is wrong.

### 5. Run and verify

```bash
uv run aegis run --all
uv run aegis score
```

Confirm the new test appears in the results with the expected status for each mock system.

### 6. Write a test

Add at least one test in `tests/` that covers the new test case's runner path. For technical tests, add a row to `tests/test_checks.py`. For evidence tests, add a row to `tests/test_evidence_runner.py`.

---

## Adding a remediation playbook

Create `aegis/remediation/REM-<ID>.yaml`:

```yaml
id: REM-FAIR-005
title: Address intersectional disparate impact

steps:
  - "Identify which attribute intersections drive the lowest selection rates using fairlearn's MetricFrame."
  - "Apply post-processing calibration with ThresholdOptimizer using an intersectional equalized_odds constraint."
  - "Re-evaluate on a held-out test set. Confirm disparate impact ratio >= 0.9 for all groups."
  - "Document the mitigation approach and residual disparity in the model card."

effort: L                              # S | M | L | XL
owner_role: ML Lead
org_wide_fix: false                    # true if one fix applies to all systems

resources:
  - "https://fairlearn.org/v0.10/user_guide/mitigation/index.html"
```

Link the playbook to its test case by setting `remediation_id: REM-FAIR-005` in the test YAML.

Validate:

```bash
uv run aegis validate
```

---

## Adding a technical metric

### 1. Create the check function

```python
# aegis/engine/checks/my_metric.py

import pandas as pd


def my_metric(df: pd.DataFrame, protected_col: str, label_col: str) -> float:
    """
    Returns a float where higher is better.
    Returns 1.0 if there is not enough data to compute.
    """
    if df.empty or protected_col not in df.columns:
        return 1.0
    # ... computation
    return result
```

Conventions:
- Accept `df: pd.DataFrame` as the first argument.
- Return a single `float`.
- Return `1.0` (safe/passing value) on empty data or missing columns — never raise.
- Use fixed random seeds if any randomness is involved.

### 2. Register in the runner

```python
# aegis/engine/runners/technical.py

from aegis.engine.checks.my_metric import my_metric

_SCALAR_CHECKS = {
    "disparate_impact_ratio": disparate_impact_ratio,
    "my_metric": my_metric,            # add here
    ...
}
```

### 3. Write tests

```python
# tests/test_checks.py

def test_my_metric_pass():
    df = pd.DataFrame({"group": ["A", "A", "B", "B"], "label": [1, 1, 1, 1]})
    assert my_metric(df, "group", "label") >= 0.9

def test_my_metric_fail():
    df = pd.DataFrame({"group": ["A", "A", "B", "B"], "label": [1, 1, 0, 0]})
    assert my_metric(df, "group", "label") < 0.8

def test_my_metric_empty():
    assert my_metric(pd.DataFrame(), "group", "label") == 1.0
```

### 4. Create a test case

Write a YAML test case with `check.metric: my_metric` and add it to the test library.

---

## Adding a new runner type

If you need a test type beyond `technical`, `evidence`, `process`, and `attestation`:

1. Create `aegis/engine/runners/<type>.py` with a function matching the signature:

```python
def run(test: dict, system: AISystem, session: Session) -> TestResult:
    ...
```

2. Register it in `aegis/engine/executor.py` in the runner dispatch map.

3. Add the new type to the `type` enum in `schemas/test_case.json`.

4. Write runner tests in `tests/test_<type>_runner.py`.

---

## Code conventions

From `CLAUDE.md`:

- Python 3.11+. Type hints everywhere. Pydantic models for every schema.
- Keep weights, thresholds and RAG bands in `scoring/config.yaml` — never hardcode them.
- Store each test at `testlib/<pillar>/<ID>.yaml` and each remediation at `remediation/<REM-ID>.yaml`.
- A runner exception → `error` result. Never `pass`.
- Wrap each metric library in a function in `engine/checks/`.
- Use fixed random seeds and pinned mock datasets for deterministic runs.
- Label all mock data with `# MOCK DATA` or `mock: true`.
- Never invent regulatory clause references. Write `TODO-verify` if unsure.
- No comments unless the WHY is non-obvious.

---

## Running the test suite

```bash
uv run pytest -q
```

138 tests currently. All must pass before merging.

Run a specific file:

```bash
uv run pytest tests/test_scoring.py -v
```

Run tests matching a pattern:

```bash
uv run pytest -k "fairness" -v
```

---

## Linting and formatting

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # lint + auto-fix
uv run ruff format .         # format
```

Ruff is configured in `pyproject.toml`. The CI gate (v0.2) will fail on any ruff error.

Run both before committing:

```bash
uv run ruff check . --fix && uv run ruff format . && uv run pytest -q
```
