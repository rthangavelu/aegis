# Aegis — AI Governance Testing Agent

Aegis treats AI governance like software QA. Governance and ethics requirements become executable test cases. Aegis runs them against your AI systems, scores the results into the **Aegis Index** (0–100), shows findings on a dashboard, and turns every failure into a concrete, prioritized fix.

> **Status:** MVP v0.1 · 41 test cases · 17 remediations · AI-powered repo scanner · MCP server · Output is an assessment, not legal advice.

---

## 5-minute quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`pip install uv` or `brew install uv`)
- Anthropic API key (for repo scanner and MCP server)

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

Executes all 41 test cases against each system in under 60 seconds.

### 5. Score

```bash
uv run aegis score
```

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

Opens a Streamlit dashboard at `http://localhost:8501` with six views:

| View | What it shows |
|---|---|
| **Scan Repo** | AI-powered scanner — point at any git repo and get a governance assessment |
| **Executive** | Org Aegis Index gauge, system RAG cards, top critical/high failures |
| **Inventory** | System × pillar heatmap (green / amber / red) |
| **Test Results** | Per-system drill-down with status, metric values and evidence |
| **Compliance** | Tests mapped to NIST AI RMF, ISO/IEC 42001 and EU AI Act |
| **Recommendations** | Prioritised improvement plan with projected uplift charts |

---

## Scan any repo

The **Scan Repo** tab (first tab in the dashboard) lets you assess any git repository without registering it in the inventory first. Claude reads the code and documentation, generates governance test cases specific to your business, executes them, and returns a scored report.

```
Repo URL or path  ──►  Extract files  ──►  Claude analyses  ──►  Generate tests  ──►  Evaluate & score
```

**Three inputs** help Claude understand your business:

1. **Repository URL or local path** — `https://github.com/org/repo` or `/path/to/local/repo`
2. **Supplementary documents** — upload PDF, DOCX, TXT or MD files (data processing agreements, model risk policies, product briefs, architecture docs)
3. **Fetch a URL** — Confluence page, public wiki, model card URL
4. **Business context** — paste a plain-English description of the system, user population, jurisdiction and regulatory obligations

The more context you provide, the more precise the generated test cases. For example, attaching a DPA causes Claude to test for the specific data retention periods it specifies; naming the user population causes fairness tests to target the right protected groups.

**Requires:** `ANTHROPIC_API_KEY` (set as env var or enter in the UI).

See [doc/repo-scanner.md](doc/repo-scanner.md) for the full pipeline and tips.

---

## Use as an AI agent (MCP)

Aegis exposes 10 tools via the Model Context Protocol so Claude Code (and any other MCP client) can run governance assessments conversationally.

```bash
uv run aegis mcp
```

Add to `~/.claude/config.json`:

```json
{
  "mcpServers": {
    "aegis": {
      "command": "uv",
      "args": ["--directory", "/path/to/aegis", "run", "aegis", "mcp"]
    }
  }
}
```

Then ask Claude Code:

> "Run an Aegis governance assessment on all systems and show me the failing critical tests."

Available tools: `list_systems`, `seed_systems`, `run_assessment`, `get_scores`, `get_test_results`, `get_failing_tests`, `get_pillar_breakdown`, `get_recommendations`, `add_system`, `validate_library`.

See [doc/mcp-server.md](doc/mcp-server.md) for the full tool reference.

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

See [doc/scoring.md](doc/scoring.md) for the complete formula and worked example.

### Pillars

| # | Pillar | Sample tests |
|---|---|---|
| 1 | Governance & Accountability | Deployment approval, model card, supply chain review (GOV-005) |
| 2 | Fairness | Disparate impact (four-fifths rule), equal opportunity, predictive parity (FAIR-004) |
| 3 | Transparency | Transparency report, model card mapping, explainability method (TRAN-004) |
| 4 | Privacy & Data | DPA, data provenance (PRIV-004), lawful basis (PRIV-005), right to erasure (PRIV-006) |
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
  cli.py                    CLI (validate, seed, run, score, recommend, dashboard, mcp)
  models.py                 Pydantic + SQLModel data models
  db.py                     SQLite engine and session factory
  mcp_server.py             MCP server (10 tools, stdio transport)
  inventory/                AI system CRUD
  engine/
    loader.py               YAML → validated test cases and remediations
    selector.py             applies_to matching (risk tier, model type, lifecycle)
    executor.py             dispatches tests, hashes evidence (SHA-256), stores results
    runners/                technical | evidence | process | attestation
    checks/                 7 metric functions (fairlearn, scikit-learn, mock)
  testlib/<pillar>/         41 YAML test cases (one file per test)
  remediation/              17 YAML playbooks (REM-*.yaml)
  schemas/                  JSON schemas for YAML validation
  scoring/
    engine.py               Aegis Index computation
    config.yaml             weights, thresholds, RAG bands, maturity bands
  recommend/
    engine.py               priority scoring, tier assignment, projected uplift
  dashboard/
    app.py                  Streamlit entry point (6 tabs)
    data.py                 cached DB queries
    views/                  executive, inventory, test_results, compliance,
                            recommendations, scanner
  scan/
    repo.py                 repo cloning, file extraction, PDF/DOCX/URL parsing
    analyzer.py             Claude-powered analysis, test generation, evaluation, scoring
  seed/
    systems.yaml            3 mock AI systems
    datasets/               CSV evaluation datasets
    documents/              mock model cards, DPAs, monitoring reports
    tickets.yaml            mock approval tickets
    attestations.yaml       mock questionnaire answers
tests/                      138 pytest tests
doc/                        full documentation
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
  - "Apply post-processing calibration (ThresholdOptimizer in fairlearn)."
  - "Re-run FAIR-005 to confirm disparate impact ratio >= 0.9."
effort: L
owner_role: ML Lead
org_wide_fix: false
```

### Add a technical metric

1. Create `aegis/engine/checks/<metric>.py` — a function accepting a `pd.DataFrame` returning a `float`.
2. Register it in `aegis/engine/runners/technical.py` under `_SCALAR_CHECKS`.
3. Write tests in `tests/test_checks.py` covering pass, warn, fail and edge cases.

See [doc/contributing.md](doc/contributing.md) for the full guide.

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
aegis dashboard                     Launch Streamlit dashboard (6 tabs)
aegis mcp                           Start MCP server (stdio transport)
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
| EU AI Act | Arts. 9, 10, 13, 14, 15, 17, 22, 25-28, 53, 72, 74 |
| GDPR | Arts. 6, 10, 17, 22 |
| FCRA / ECOA | US credit decisioning |
| HIPAA | US health data |
| CCPA | US consumer privacy |

---

## Roadmap

**v0.2** — Real system connectors (MLflow model registry, Jira/Linear tickets, Confluence docs), scheduled runs, GitHub Actions CI gate, LLM red-team suite, audit pack PDF export  
**v0.3** — REL-005 output drift (connector-based data), Wave 3 tests (intersectional fairness, data lineage, model card auto-generation)  
**v1.0** — FastAPI service, React dashboard, multi-tenancy, industry benchmarks, SOC 2 / ISO 42001 audit report export

---

## Documentation

| Doc | Contents |
|---|---|
| [doc/architecture.md](doc/architecture.md) | System design, data model, data flow, two operating modes |
| [doc/scoring.md](doc/scoring.md) | Aegis Index formula, worked example, RAG bands, maturity levels |
| [doc/test-library.md](doc/test-library.md) | All 41 test cases, YAML schema, technical checks reference |
| [doc/repo-scanner.md](doc/repo-scanner.md) | AI-powered scanner pipeline, supplementary docs, tips |
| [doc/dashboard.md](doc/dashboard.md) | Dashboard user guide, tab-by-tab walkthrough |
| [doc/mcp-server.md](doc/mcp-server.md) | MCP server setup, all 10 tools, example conversation |
| [doc/cli.md](doc/cli.md) | Full CLI reference with flags and example output |
| [doc/contributing.md](doc/contributing.md) | Adding tests, remediations, metrics; code conventions |

---

## About

Built by [Flowwolf](https://flowwolf.io) using Claude Code.  
See `INTENT.md` for the full scope, scoring rules (§8), recommendation rules (§9) and acceptance criteria (§10).
