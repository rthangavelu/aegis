# Aegis — Project Intent

> **One line:** Aegis is an AI governance and ethics testing agent. It runs test cases against a company's AI systems and governance processes, scores the results, shows them on a dashboard, and recommends how to improve.

| | |
|---|---|
| **Owner** | Raji (Flowwolf) |
| **Status** | Intent / pre-build |
| **Build tool** | Claude Code |
| **Last updated** | 2026-11-13 |

---

## 1. Why we are building this

Companies are deploying AI faster than they can govern it. Regulations and standards such as the EU AI Act, ISO/IEC 42001 and the NIST AI RMF expect organizations to prove that their AI is fair, transparent, safe, private and overseen by humans. Today that proof is mostly spreadsheets, questionnaires and one-off audits. These are slow and subjective, and they are out of date as soon as a model changes.

**Aegis treats AI governance like software QA.** Governance and ethics requirements become executable test cases. Aegis runs them repeatedly, scores the results consistently, and turns every failure into a concrete fix.

## 2. Who it is for

| User | What they need from Aegis |
|---|---|
| Executives and the board | One trustworthy number (the Aegis Index), the top risks, and whether we are improving |
| Risk, compliance and legal | Control coverage against the regulations, plus audit-ready evidence |
| ML and engineering teams | Specific failing tests, metric values, and a fix that fits their system |
| AI governance lead | Inventory of all AI systems, trends, and who owns which actions |

## 3. Goals

1. **Executable governance.** Express governance and ethics controls as versioned test cases in YAML, and run them automatically.
2. **Consistent scoring.** The same inputs always produce the same score. The scoring is explainable and rolls up from system to business unit to company.
3. **Actionable dashboard.** Show the views each audience needs, and let users drill from any score down to the evidence.
4. **Recommendations, not just findings.** Every failure links to a prioritized remediation with an owner, the effort, the projected score uplift, and the test that verifies the fix.
5. **Regulation-mapped.** Every test maps to clauses in NIST AI RMF, ISO/IEC 42001 and/or the EU AI Act, so one run produces evidence for several frameworks.

## 4. Non-goals (for now)

- Aegis does not give legal advice or certify compliance. It produces evidence and assessments.
- It does not train or fix models itself. It recommends and verifies.
- No multi-tenant SaaS, billing or SSO in the MVP.
- No real customer data in the MVP. It uses seeded mock systems and data.

## 5. Core concepts

- **AI System:** an entry in the inventory, with an owner, purpose, model type, risk tier (unacceptable / high / limited / minimal), lifecycle stage, endpoint and evaluation dataset.
- **Pillar:** one of 9 areas:
  - Governance & Accountability
  - Fairness & Bias
  - Transparency & Explainability
  - Privacy & Data
  - Safety & Security
  - Reliability & Monitoring
  - Human Oversight
  - GenAI-specific
  - Training & Culture
- **Test Case:** a YAML definition with an id, pillar, type, severity, applicability rules, regulatory mappings, check and thresholds, and a remediation link. There are four types:
  - `technical`: measures model behaviour with data
  - `evidence`: checks that an artifact exists, is current and is complete
  - `process`: checks that a workflow was followed
  - `attestation`: a human confirms, with evidence
- **Test Result:** pass / warn / fail / na / pending / error, plus the metric value, an evidence URI and the evidence hash.
- **Aegis Index:** the 0–100 Responsible AI score, calculated per pillar, per system, per business unit and for the whole organization.
- **Remediation:** a playbook entry for a failed test: steps, effort (S/M/L), owner role, and whether the fix is organization-wide.

## 6. Scope: MVP (v0.1)

### Must have

1. **AI inventory:** CRUD through the CLI and API, stored in SQLite. Seeded with 3 mock systems:
   - `credit-scoring-v3`: high-risk classification model
   - `support-chatbot`: limited-risk LLM
   - `resume-screener`: high-risk classification model
2. **Test library:** at least 30 YAML tests covering all 9 pillars, validated against a JSON Schema.
3. **Test engine:** loads tests, selects the ones that apply to each system, runs them, and stores the results.
   - Evidence runner: checks mock documents
   - Attestation runner: reads mock questionnaire answers
   - Process runner: reads mock tickets and approvals
   - Technical runner: at least 3 checks, namely disparate impact, equal opportunity difference and accuracy floor (using fairlearn), plus 1 mock LLM jailbreak-rate check
4. **Scoring engine:** the rules in section 8, configurable in YAML, with unit tests for each rule.
5. **Dashboard (Streamlit):** Executive, Inventory heatmap, Test results, Compliance mapping and Recommendations views.
6. **Recommendation engine:** playbook lookup, priority score, root-cause grouping and projected uplift.
7. **CLI:** `aegis run`, `aegis score`, `aegis recommend`, `aegis dashboard` and `aegis validate`.
8. **Exports:** results as CSV, and the improvement plan as Markdown.

### Should have (v0.2)

- Connectors for MLflow, Jira and Confluence/SharePoint
- Scheduled runs
- A GitHub Actions CI gate that fails on any critical test failure
- An LLM red-team suite using garak or promptfoo
- LLM-tailored recommendations
- An audit pack export (PDF with evidence hashes)
- A trends view

### Later (v0.3+)

- A FastAPI service and a React dashboard
- Multi-tenancy
- Industry benchmarks
- Custom test authoring UI
- **Harness² optimization:** once Aegis has a stable eval set, use google-research/harness2 to tune Aegis's prompts and skills.

## 7. Architecture

```
Connectors ─▶ Test Engine ─▶ Scoring Engine ─▶ Dashboard ◀─ Recommendation Engine
                  ▲
   Test Library (YAML + JSON Schema, mapped to NIST / ISO 42001 / EU AI Act)
   AI System Inventory
```

### Stack

- Python 3.11+ with uv
- pydantic and SQLite (via SQLModel)
- Typer for the CLI
- Streamlit and Plotly for the dashboard
- fairlearn, scikit-learn and pandas for the technical checks
- pytest and ruff for testing and linting

### Repository layout

```
aegis/
  inventory/ testlib/<pillar>/ remediation/ schemas/
  engine/{loader,selector,executor}.py  engine/runners/  engine/checks/
  connectors/ scoring/ recommend/ dashboard/ cli.py
  seed/            # mock systems, datasets, documents, tickets, attestations
tests/
.claude/skills/    # aegis-builder, aegis-test-author, aegis-report
```

## 8. Scoring rules

1. **Points:** pass = 1, warn = 0.5, fail = 0. `na` and `pending` are excluded from the score. `error` counts as fail and is also flagged separately.
2. **Severity weights:** critical 4, high 3, medium 2, low 1.
3. **Risk-tier multiplier:** high 1.5, limited 1.0, minimal 0.5.
4. **Pillar score** = 100 × Σ(points × weight) / Σ(weight).
5. **Maturity:**
   - 0–20 → 1 (Initial)
   - 21–40 → 2 (Repeatable)
   - 41–60 → 3 (Defined)
   - 61–80 → 4 (Managed)
   - 81–100 → 5 (Optimized)
6. **Aegis Index** = the weighted average of the pillar scores. Weights are equal by default and configurable.
7. **Critical cap:** any failed critical test makes that system RED, whatever its index.
8. **RAG status:** Green ≥ 80, Amber 60–79, Red < 60 or any critical failure.
9. **Roll-up:** systems roll up to business units and then to the organization, weighted by the risk-tier multiplier.

## 9. Recommendation rules

- **Priority** = severity weight × risk multiplier × number of systems affected ÷ effort factor, where S = 1, M = 2 and L = 4. Any failed critical test is P0.
- **Root-cause grouping:** if the same test fails on 3 or more systems, or the remediation is marked `org_wide_fix`, it becomes one organization-level action.
- **Tiers:**
  - P0
  - Quick wins (high priority, effort S)
  - Strategic (effort L)
  - Hygiene (everything else)
- Every recommendation shows the projected index before → after, and the test ID that verifies the fix.

## 10. Acceptance criteria for the MVP

- [ ] `uv run aegis validate` passes for all tests and remediations.
- [ ] `uv run aegis run --all` runs the full library against the 3 seeded systems in under 60 seconds, with no `error` results.
- [ ] The seeded data is designed so that `resume-screener` **fails** FAIR-001 (disparate impact) and is RED, and `support-chatbot` is AMBER. This proves the framework can detect problems.
- [ ] Running the same command twice produces identical scores.
- [ ] The dashboard opens with `uv run aegis dashboard` and shows all 5 views, with a drill-down from the index to the evidence.
- [ ] `aegis recommend` outputs a prioritized plan: P0 items first, root-cause groups, projected uplift and a 30/60/90-day roadmap.
- [ ] pytest coverage is at least 80% for `scoring/` and `recommend/`, and ruff passes cleanly.
- [ ] The README has a 5-minute quickstart.

## 11. Guardrails and principles

- Never report a test as passing if it didn't run. Errors are surfaced, never hidden.
- Never invent regulatory clause numbers. Use `TODO-verify` when unsure.
- Mock data is clearly labelled as mock everywhere it appears.
- No secrets in the repo. Connectors read credentials from environment variables.
- Every result stores a SHA-256 hash of its evidence, for audits.
- The output is an assessment, not legal advice. The dashboard footer says so.

## 12. Milestones

| Milestone | Outcome |
|---|---|
| M1: Foundations | Repo scaffold, schemas, loader/validator, inventory and seed data |
| M2: Engine | Selector, executor and the 4 runners; 30 tests |
| M3: Scoring | Scoring engine and its unit tests; `aegis score` |
| M4: Recommendations | Playbooks, prioritization and the Markdown plan |
| M5: Dashboard | The 5 Streamlit views; acceptance criteria met |

## 13. Open questions

1. Which industry should the first real pilot be: finance (credit) or HR (hiring)?
2. Should pillar weights stay equal, or follow the company's risk appetite?
3. Which ticketing tool should be integrated first: Jira or ServiceNow?
4. Which LLM provider should be used for the evidence-quality rubric and recommendation tailoring?
