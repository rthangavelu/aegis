# Aegis — AI Governance Testing Agent

Aegis treats AI governance like software QA. Governance and ethics requirements become executable test cases. Aegis runs them against your AI systems, scores the results into the **Aegis Index** (0–100), shows the findings on a dashboard, and turns every failure into a concrete, prioritized fix.

> **Status:** MVP v0.1 · 41 test cases · 17 remediations · Mock systems only · Output is an assessment, not legal advice.

---

## 5-minute quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`pip install uv` or `brew install uv`)

### 1. Install

```bash
git clone <repo>
cd aegis
uv sync
```

### 2. Validate the test library

```bash
uv run aegis validate
```

Expected: `41 test case(s) valid · 17 remediation(s) valid`

### 3. Seed mock systems

```bash
uv run aegis seed
```

Loads three mock AI systems into a local SQLite database:

| System | Risk tier | Expected result |
|---|---|---|
| `credit-scoring-v3` | High | Green (100.0) — all 32 applicable tests pass |
| `support-chatbot` | Limited | Amber (67.2) — GenAI warns, transparency docs missing |
| `resume-screener` | High | Red (20.6) — FAIR-001 critical fail + 16 further failures |

### 4. Run tests

```bash
uv run aegis run --all
```

Executes all 41 test cases against each system in under 60 seconds with no errors.

### 5. Score

```bash
uv run aegis score
```

Computes the Aegis Index per pillar, per system and for the whole organisation:

```
System               Index   Maturity   RAG
credit-scoring-v3    100.0      5       Green
support-chatbot       67.2      4       Amber
resume-screener       20.6      2       Red
```

Organisation Aegis Index: **62.0 / 100** · Red · Maturity 4/5

### 6. Recommend

```bash
uv run aegis recommend
```

Writes `improvement_plan.md` — a prioritised remediation plan with P0 items first, projected score uplift, owner roles, effort estimates and a 30/60/90-day roadmap.

### 7. Open the dashboard

```bash
uv run aegis dashboard
```

Opens a Streamlit dashboard at `http://localhost:8501` with five views:

| View | What it shows |
|---|---|
| **Executive** | Org Aegis Index gauge, system RAG cards, top critical/high failures |
| **Inventory** | System × pillar heatmap (green / amber / red) |
| **Test Results** | Per-system drill-down with status, metric values and evidence |
| **Compliance** | Tests mapped to NIST AI RMF, ISO/IEC 42001 and EU AI Act |
| **Recommendations** | Prioritised improvement plan with projected uplift charts |

---

## How it works

### Aegis Index

```
Test result (pass/warn/fail)
  → weighted by severity  (critical=4, high=3, medium=2, low=1)
  → pillar score = 100 × Σ(points × weight) / Σ(weight)
  → system Aegis Index = weighted average of pillar scores
  → roll-up: system → business unit → organisation (weighted by risk tier)
```

**RAG:** Green ≥ 80 · Amber 60–79 · Red < 60 or any critical failure  
**Maturity:** 1 Initial · 2 Repeatable · 3 Defined · 4 Managed · 5 Optimised

### Pillars

| # | Pillar | Sample tests |
|---|---|---|
| 1 | Governance & Accountability | Deployment approval, model card, supply chain review (GOV-005) |
| 2 | Fairness | Disparate impact (four-fifths rule), equal opportunity, FPR parity (FAIR-004) |
| 3 | Transparency | Transparency report, model card mapping, explainability method (TRAN-004) |
| 4 | Privacy & Data | Data protection agreement, data provenance (PRIV-004), lawful basis (PRIV-005), right to erasure (PRIV-006) |
| 5 | Safety & Security | Risk assessment, adversarial testing, post-market surveillance (SAFE-004) |
| 6 | Reliability | Accuracy floor, monitoring dashboard, prediction drift (REL-004) |
| 7 | Human Oversight | Override log, human review attestation, appeal/recourse (HUM-004) |
| 8 | GenAI-specific | Jailbreak rate, hallucination controls, GPAI copyright policy (GENAI-007) |
| 9 | Training & Culture | AI ethics training completion, policy acknowledgment |

### Test types

| Type | How it works |
|---|---|
| `technical` | Computes metrics with fairlearn/scikit-learn against an eval dataset |
| `evidence` | Checks that a document exists, is recent and contains required sections |
| `process` | Checks tickets and approvals in seed data or connectors |
| `attestation` | Reads human questionnaire answers; `pending` if no answer or expired |

---

## Project layout

```
aegis/
  cli.py                    # CLI (validate, seed, run, score, recommend, dashboard)
  models.py                 # Pydantic + SQLModel data models
  db.py                     # SQLite engine and session factory
  inventory/                # AI system CRUD
  engine/
    loader.py               # YAML → validated test cases and remediations
    selector.py             # applies_to matching (risk tier, model type, lifecycle)
    executor.py             # dispatches tests, hashes evidence (SHA-256), stores results
    runners/                # technical | evidence | process | attestation
    checks/                 # disparate_impact, equal_opportunity, accuracy, jailbreak, pii_leak, drift, predictive_parity
  testlib/<pillar>/         # YAML test cases (one file per test, validated against schemas/)
  remediation/              # YAML playbooks (REM-*.yaml)
  scoring/
    engine.py               # Aegis Index computation (INTENT.md §8)
    config.yaml             # Weights, thresholds, RAG bands, maturity bands
  recommend/
    engine.py               # Priority scoring, tier assignment, projected uplift (INTENT.md §9)
  dashboard/
    app.py                  # Streamlit entry point
    data.py                 # Cached DB queries
    views/                  # executive, inventory, test_results, compliance, recommendations
  seed/
    systems.yaml            # 3 mock AI systems
    datasets/               # CSV evaluation datasets
    documents/              # Mock model cards, DPAs, monitoring reports
    tickets.yaml            # Mock approval tickets
    attestations.yaml       # Mock questionnaire answers
tests/                      # pytest suite (138 tests)
```

---

## Extending Aegis

### Add a test case

Create `aegis/testlib/<pillar>/<ID>.yaml`:

```yaml
id: FAIR-005
name: Intersectional disparate impact check
pillar: Fairness
type: technical
severity: high
applies_to:
  risk_tier: [high, unacceptable]
  model_type: [classification]
mappings:
  - framework: NIST_AI_RMF
    ref: "MEASURE 2.11"
  - framework: EU_AI_ACT
    ref: "Art. 10(2)"
inputs:
  dataset: "${system.eval_dataset}"
  protected_attributes: [gender, age_band]
check:
  metric: disparate_impact_ratio
  aggregate: min
  threshold:
    pass: ">= 0.9"
    warn: ">= 0.8"
remediation_id: REM-FAIR-001
owner_role: ML Lead
version: 1
```

Run `uv run aegis validate` to confirm the schema is valid.

### Add a remediation playbook

Create `aegis/remediation/REM-<ID>.yaml`:

```yaml
id: REM-FAIR-005
title: Address intersectional disparate impact
steps:
  - "Identify which attribute intersections drive the lowest selection rates."
  - "Apply post-processing calibration (ThresholdOptimizer in fairlearn) with
     intersectional constraints."
  - "Re-run FAIR-005 to confirm disparate impact ratio >= 0.9."
effort: L
owner_role: ML Lead
org_wide_fix: false
resources:
  - "https://fairlearn.org/v0.10/user_guide/mitigation/index.html"
```

### Add a new technical metric

1. Create `aegis/engine/checks/<check_name>.py` with a function that accepts a `pd.DataFrame` and returns a `float`.
2. Register it in `aegis/engine/runners/technical.py` under `_SCALAR_CHECKS` (or add an `elif` block for metrics that need extra inputs).
3. Write tests in `tests/test_checks.py` covering pass, warn, fail and edge cases.

---

## CLI reference

```
aegis validate                      Validate test cases and remediations
aegis seed                          Load mock AI systems
aegis inventory                     List AI systems
aegis run --all                     Run all tests against all systems
aegis run --system <id>             Run tests against one system
aegis score [--run-id <id>]         Compute Aegis Index scores
aegis recommend [--run-id <id>]     Generate improvement plan (improvement_plan.md)
aegis dashboard                     Launch Streamlit dashboard
```

---

## Tests and linting

```bash
uv run pytest -q           # 138 tests
uv run ruff check .        # linting
uv run ruff format .       # formatting
```

---

## Regulatory coverage

| Framework | Coverage |
|---|---|
| NIST AI RMF | GOVERN 1.1–6.2, MAP 1–5, MEASURE 2.1–2.13, MANAGE 1–4 |
| ISO/IEC 42001 | Clauses 5–10, Annex A.4–A.10 |
| EU AI Act | Arts. 9, 10, 13, 14, 15, 17, 22, 25-28, 53, 72 |

---

## Roadmap

**v0.2** — Real system connectors (MLflow model registry, Jira/Linear tickets, Confluence docs), scheduled runs, GitHub Actions CI gate, LLM red-team suite, audit pack PDF export  
**v0.3** — REL-005 output drift (connector-based data), Wave 3 tests (intersectional fairness, data lineage, model card auto-generation)  
**v1.0** — FastAPI service, React dashboard, multi-tenancy, industry benchmarks, SOC 2 / ISO 42001 audit report export

---

## About

Built by [Flowwolf](https://flowwolf.io) using Claude Code.  
See `INTENT.md` for the full scope, scoring rules (§8), recommendation rules (§9) and acceptance criteria (§10).

---

## Building with Claude Code

If you are continuing to develop Aegis with Claude Code:

```bash
cd Aegis
claude
```

Kick off a milestone with:

> Read INTENT.md and CLAUDE.md. Use the aegis-builder skill. Implement M\<N\> with passing tests, then stop and summarize.

Use the `aegis-test-author` skill to grow the test library and `aegis-report` to run assessments and interpret results.
