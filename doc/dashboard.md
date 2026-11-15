# Dashboard

This document is a tab-by-tab guide to the Aegis Streamlit dashboard.

---

## Launching

```bash
uv run aegis dashboard
```

Opens at `http://localhost:8501`. The dashboard reads from the local SQLite database (`aegis.db`). If no test run exists, tabs 2–6 show a setup prompt; the Scan Repo tab (tab 1) is always available.

To populate the persistent tabs, run:

```bash
uv run aegis seed && uv run aegis run --all && uv run aegis score
```

---

## Tab 1: Scan Repo

**Entry point for assessing any AI repository without prior setup.**

### Input form

| Field | Required | Description |
|---|---|---|
| Repository URL or local path | Yes | `https://github.com/org/repo` or `/absolute/path/to/repo` |
| Branch | No | Defaults to the repo's default branch |
| Anthropic API key | Yes* | Enter here or set `ANTHROPIC_API_KEY` env var before launching |
| Upload documents | No | PDF, DOCX, TXT, MD — see [repo-scanner.md](repo-scanner.md) |
| Fetch a URL | No | Confluence page, model card URL, public wiki |
| Business context | No | Plain-text description of the business, users, jurisdiction |

*If `ANTHROPIC_API_KEY` is set in the environment before launching, the field can be left blank.

### Progress display

After clicking **Scan & Assess**, an expandable status panel shows each of the 5 stages in real time. If a stage fails (e.g. clone error, API error), it shows an error and stops. Each stage reports its duration.

### Results

After the scan completes:

- **Header row** — Aegis Index, RAG badge (coloured), Pass/Warn/Fail counts
- **System summary** — Domain name, 2–3 sentence description, AI system cards (one per detected system, colour-coded by risk level)
- **Pillar bar chart** — Score for each pillar that has test results, coloured Green/Amber/Red
- **Governance gaps** — List of concerns Claude identified directly from the repo content
- **Test results** — Filterable by status, severity, and pillar

### Test result rows

Each row is expandable and shows:

- **Finding** — what Claude found (or didn't find) in the repo, in a coloured box
- **Evidence** — specific file path where the evidence was (or wasn't) located
- **Why it matters** — the real-world harm if this test fails, specific to the detected AI system
- **How to improve** — numbered list of concrete remediation steps

---

## Tab 2: Executive

**High-level governance health for leadership and governance committees.**

### Org Aegis Index gauge

A Plotly gauge chart showing the overall organisation Aegis Index (0–100) with the RAG colour band. The needle position and colour give an at-a-glance status.

### System score bars

Horizontal bar chart showing each system's Aegis Index, sorted descending. Bars are coloured Green/Amber/Red. Useful for identifying the weakest systems at a glance.

### RAG cards

One card per system. Each card shows:
- System name and business unit
- Aegis Index and maturity level
- RAG badge
- Fail and warn counts

Cards are sorted Red → Amber → Green so the most critical systems appear first.

### Critical and high failures table

A table of all `fail` results with severity `critical` or `high` across all systems. Columns: system, test ID, test name, pillar, severity. This is the action list for immediate remediation.

---

## Tab 3: Inventory

**System × pillar heatmap for identifying coverage gaps and weak pillars.**

### Heatmap

A Plotly heatmap with systems on the Y axis and the 9 pillars on the X axis. Cell colour:

| Colour | Meaning |
|---|---|
| Green | Pillar score ≥ 80 |
| Amber | Pillar score 60–79 |
| Red | Pillar score < 60 or critical failure |
| Grey | No applicable tests for this system/pillar combination |

Hover over a cell to see the exact score. Click a cell to filter the Test Results tab (feature coming in v0.2).

### System inventory table

Below the heatmap: a table of all registered systems with columns for risk tier, model type, lifecycle stage, owner, business unit, and whether the system is mock data.

---

## Tab 4: Test Results

**Per-system test result drill-down with evidence and metric values.**

### Filters

| Filter | Options |
|---|---|
| System | Dropdown of all systems in the latest run |
| Status | Multiselect: pass, warn, fail, na, pending, error (defaults to fail + warn) |
| Pillar | Multiselect of all 9 pillars |

### Results table

Columns: Test ID, Name, Pillar, Type, Severity, Status, Metric Value, Threshold, Message.

Status is colour-coded: green for pass, amber for warn, red for fail/error.

### Evidence expanders

Each row is expandable. Expanding a row shows:
- Evidence URI (file path or URL)
- SHA-256 hash of the evidence file at the time of the run

The hash lets you verify that the evidence file hasn't changed since the test was run.

---

## Tab 5: Compliance

**Tests mapped to regulatory frameworks.**

Three sub-tabs: **NIST AI RMF**, **ISO/IEC 42001**, **EU AI Act**.

Each sub-tab shows a matrix of framework references (rows) × systems (columns). Each cell contains a status symbol:

| Symbol | Meaning |
|---|---|
| ✓ | All tests for this ref passed |
| ⚠ | At least one test warned |
| ✗ | At least one test failed |
| — | No tests mapped to this ref for this system |
| ⏳ | Tests pending (attestation not yet answered) |
| ⚡ | Test errored |

A coverage count shows how many framework references have at least one mapped test for each system.

**Limitations:** coverage is based on the YAML `mappings` in the test library. References not mapped to any test show `—`. This is not a certification of compliance — it shows test coverage and results against the references.

---

## Tab 6: Recommendations

**Prioritised improvement plan with projected score impact.**

### Summary metrics

Five columns: Total recommendations, P0 (critical), Quick wins, Strategic, Hygiene.

### Top uplifts chart

Horizontal bar chart showing the top 10 recommendations by projected Aegis Index uplift (in points). Coloured by tier.

### Tier sections

Recommendations are grouped into four tiers, each in a collapsible section:

| Tier | Definition |
|---|---|
| **P0** | Critical failures — fix immediately |
| **Quick win** | High impact, low effort |
| **Strategic** | High impact, high effort — plan for 60–90 days |
| **Hygiene** | Low impact, low effort — good practice |

Each recommendation card shows:
- Title and test ID
- Pillar and severity
- Effort estimate (S/M/L/XL) and owner role
- Current Aegis Index → projected Aegis Index after fix
- Systems affected
- Remediation steps

### 30/60/90-day roadmap

Three columns showing which recommendations to address in each time window:
- **30 days** — P0 items and quick wins
- **60 days** — strategic items with shorter lead time
- **90 days** — longer strategic items and hygiene
