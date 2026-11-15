# Architecture

This document covers Aegis system design, component responsibilities, data flow, data model, and operating modes.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Aegis                                     │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ Inventory│──►│  Engine  │──►│ Scoring  │──►│ Recommendations│  │
│  │  (CRUD)  │   │(test run)│   │ (index)  │   │  (plan + uplift)│  │
│  └──────────┘   └──────────┘   └──────────┘   └────────────────┘  │
│       ▲               │               │               │            │
│       │          ┌────▼───────────────▼───────────────▼────┐      │
│  ┌────┴────┐     │              SQLite DB                   │      │
│  │  CLI /  │     │  (AISystem, TestRun, TestResult, Score,  │      │
│  │   MCP   │     │   Recommendation)                        │      │
│  └─────────┘     └──────────────────────────────────────────┘      │
│                                       │                            │
│  ┌─────────────────────────────────── ▼ ────────────────────────┐  │
│  │                   Streamlit Dashboard                        │  │
│  │  Scan Repo │ Executive │ Inventory │ Results │ Compliance │  │  │
│  │            │           │          │ Recs     │            │  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │               AI-Powered Repo Scanner (scan/)              │    │
│  │   clone → extract → Claude analyse → generate → evaluate  │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Operating modes

Aegis has two distinct modes. They share the scoring formula but differ in persistence.

### Mode 1: Persistent inventory mode

Used by the CLI and dashboard tabs 2–6.

1. AI systems are registered in SQLite via `aegis seed` or `aegis inventory add`.
2. `aegis run` executes YAML test cases against each system and stores `TestResult` rows.
3. `aegis score` reads results and writes `Score` rows (per pillar, per system, per BU, org-wide).
4. `aegis recommend` reads failing scores and writes `Recommendation` rows.
5. The dashboard reads all of this from SQLite via cached queries in `dashboard/data.py`.

**Storage:** SQLite at `aegis.db` in the working directory.

### Mode 2: Repo scan mode (ephemeral)

Used by the **Scan Repo** dashboard tab.

1. User provides a repo URL/path and optional supplementary documents.
2. `scan/repo.py` clones or reads the repo and extracts governance-relevant files.
3. `scan/analyzer.py` calls Claude three times: analyse → generate tests → evaluate each test.
4. `compute_scan_scores()` applies the same Aegis Index formula to the results.
5. Results are stored in Streamlit session state only — not persisted to SQLite.

**Storage:** Streamlit `st.session_state` (cleared on browser refresh).

---

## Component descriptions

### `cli.py`
Typer-based CLI entry point. Each subcommand delegates to the appropriate module. The `mcp` command starts the MCP server over stdio.

### `models.py`
Pydantic + SQLModel definitions for all database entities. Enums enforce valid values for `ModelType`, `RiskTier`, `LifecycleStage`, `TestStatus`, `RAGStatus`.

### `db.py`
SQLite engine and session factory. `init_db()` creates tables if they don't exist. `get_session()` is a context manager returning a SQLModel session.

### `inventory/`
CRUD for `AISystem`. `seed_inventory()` loads `seed/systems.yaml` and upserts the three mock systems. `upsert_system()` is used by `add_system` MCP tool.

### `engine/`

| File | Responsibility |
|---|---|
| `loader.py` | Reads YAML from `testlib/` and `remediation/`, validates against `schemas/*.json`, returns typed dicts |
| `selector.py` | Matches a test's `applies_to` block against system fields (risk tier, model type, lifecycle stage). Non-matching tests get status `na`. |
| `executor.py` | Iterates over applicable tests, dispatches to the correct runner, catches exceptions (→ `error`), computes SHA-256 evidence hash, writes `TestResult` rows |
| `runners/technical.py` | Loads eval dataset CSV, calls the appropriate check function from `checks/`, compares output to pass/warn thresholds |
| `runners/evidence.py` | Checks document existence, freshness (modified date), and required section headers |
| `runners/process.py` | Reads approval tickets from seed data or connectors |
| `runners/attestation.py` | Reads questionnaire answers; `pending` if no answer or answer expired |
| `checks/` | One function per metric: `disparate_impact_ratio`, `equal_opportunity_difference`, `accuracy_floor`, `jailbreak_rate`, `pii_leak_rate`, `drift`, `predictive_parity` |

### `testlib/<pillar>/`
41 YAML files, one per test case. Schema validated by `loader.py`. See [test-library.md](test-library.md) for the full list and schema.

### `remediation/`
17 YAML playbooks. Each has `id`, `title`, `steps[]`, `effort` (S/M/L/XL), `owner_role`, `org_wide_fix`, optional `resources[]`.

### `scoring/`
`engine.py` reads `TestResult` rows for a run and computes `Score` rows using the formula in `config.yaml`. Writes one `Score` per (run, scope, pillar) tuple. `config.yaml` holds severity weights, RAG bands, maturity bands — never hardcoded.

### `recommend/`
`engine.py` reads failing `Score` and `TestResult` rows. Prioritises by `severity × num_systems_affected`. Assigns tiers (P0 = critical fail, quick_win = high impact + low effort, strategic = high impact + high effort, hygiene = low impact). Computes projected uplift in Aegis Index points.

### `dashboard/`
Streamlit app. `app.py` sets page config and renders 6 tabs. `data.py` provides `@st.cache_data`-wrapped DB query functions with 30s TTL. Each view module has a single `render()` function. `views/scanner.py` runs the ephemeral scan pipeline with `st.status()` live progress.

### `scan/`
`repo.py` — clones remote repos with `git clone --depth 1`, extracts priority files (README, model cards, `*.md`, AI-keyword Python files, dependency manifests), reads uploaded PDFs/DOCX/text, fetches URLs.  
`analyzer.py` — three Claude API calls: analyse repo → generate test cases → evaluate each test. `compute_scan_scores()` applies standard Aegis weighting.

### `mcp_server.py`
`MCPServer` from `mcp.server.mcpserver`. 10 `@server.tool()` decorated functions. Transport: stdio (`server.run_stdio_async()`). No HTTP listener in v0.1.

---

## Data model

```
AISystem
  id              str (PK, slug e.g. "resume-screener")
  name            str
  owner           str
  business_unit   str
  purpose         str
  model_type      ModelType  (classification|regression|llm|recommender|other)
  risk_tier       RiskTier   (unacceptable|high|limited|minimal)
  lifecycle_stage LifecycleStage (development|testing|production|deprecated)
  endpoint        str | None
  eval_dataset    str | None  (path to CSV)
  data_sources    list[str]
  jurisdictions   list[str]
  mock            bool

TestRun
  id              str (PK, UUID)
  started_at      datetime
  finished_at     datetime | None
  trigger         str  (manual|schedule|ci)
  scope           str

TestResult
  run_id          str (FK → TestRun)
  system_id       str (FK → AISystem)
  test_id         str  (e.g. "FAIR-001")
  status          TestStatus  (pass|warn|fail|na|pending|error)
  metric_value    float | None
  threshold       float | None
  evidence_uri    str | None
  evidence_hash   str | None  (SHA-256)
  message         str | None
  executed_at     datetime

Score
  run_id          str (FK → TestRun)
  scope           str  (system|bu|org)
  scope_id        str  (system id, BU name, or "org")
  pillar          str  (pillar name or "overall")
  score           float  (0–100)
  maturity        int  (1–5)
  rag             RAGStatus  (Green|Amber|Red)
```

---

## Data flow (persistent mode)

```
seed/systems.yaml
       │
       ▼
  AISystem rows ──► selector.py (applies_to match) ──► TestResult rows (na/skip)
                           │
              testlib/*.yaml ──► executor.py ──► runners/ ──► checks/
                                       │
                                  TestResult rows (pass/warn/fail/error)
                                       │
                                  scoring/engine.py
                                       │
                                   Score rows
                                       │
                              recommend/engine.py
                                       │
                              Recommendation rows
                                       │
                              dashboard/data.py (cached)
                                       │
                              Streamlit views
```

---

## Dependencies

| Package | Used for |
|---|---|
| `pydantic` + `sqlmodel` | Data models and ORM |
| `typer` + `rich` | CLI |
| `streamlit` | Dashboard |
| `plotly` | Charts |
| `fairlearn` | Disparate impact, equal opportunity metrics |
| `scikit-learn` | Accuracy, calibration |
| `pandas` | Dataset loading |
| `anthropic` | Claude API (repo scanner) |
| `pypdf` | PDF extraction (repo scanner) |
| `python-docx` | DOCX extraction (repo scanner) |
| `mcp` | MCP server |
| `pytest` | Test suite |
| `ruff` | Linting and formatting |
