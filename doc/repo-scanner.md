# Repo Scanner

This document covers the AI-powered repository scanner: what it does, how the pipeline works, how to get the best results, and its limitations.

---

## What problem it solves

Most organisations don't have an Aegis inventory yet. The repo scanner lets you assess any AI/ML code repository immediately — without registering a system, without seed data, without prior setup. Point it at a GitHub repo and get a scored governance report in minutes.

The scan is also useful for:
- Due diligence on third-party AI components
- Quick governance baseline before onboarding a system into the full inventory
- Developers who want to self-assess before a formal review

---

## Pipeline

The scanner runs 5 stages, all shown in real time in the dashboard using `st.status()`.

```
Stage 1: Access repo
  └── git clone --depth 1 <url>  OR  validate local path

Stage 2: Extract AI-relevant files
  └── Priority files (README, model cards, ethics docs)
  └── All *.md files
  └── Python files with AI-keyword names (model, train, pipeline, …)
  └── Dependency files (requirements.txt, pyproject.toml, package.json)
  └── AI-keyword YAML/JSON config files
  └── Supplementary documents (uploaded PDFs/DOCX, fetched URLs)
  └── Free-text business context

Stage 3: Claude analyses the repo
  └── Identifies AI systems (name, purpose, model type, risk level)
  └── Detects business domain and decision impact
  └── Finds governance gaps visible right now
  └── Determines applicable regulations

Stage 4: Claude generates 12–15 test cases
  └── Specific to the detected business domain and AI systems
  └── Informed by supplementary documents and business context
  └── Distributed across the 9 Aegis pillars

Stage 5: Claude evaluates each test
  └── Checks the extracted repo content against each test criterion
  └── Returns: status (pass/warn/fail/na), finding, evidence location,
      explanation, improvement steps
  └── Progress bar shows test-by-test execution
```

**Result:** Aegis Index score (0–100), RAG badge, pillar bar chart, AI system cards, expandable test result rows.

---

## File extraction

Files are extracted in priority order and capped at 8,000 chars per file, 80,000 chars total.

| Priority | Files |
|---|---|
| 1 — Highest | `README.md`, `README.rst`, `README.txt`, `ETHICS.md`, `GOVERNANCE.md`, `FAIRNESS.md`, `SAFETY.md`, `MODEL_CARD.md`, `model_card.md`, `DATA_PROCESSING.md`, `PRIVACY.md`, `SECURITY.md`, `CONTRIBUTING.md` |
| 2 | All `*.md` files in the repo |
| 3 | Python files whose filename contains AI keywords: `model`, `train`, `inference`, `predict`, `classifier`, `neural`, `embedding`, `tokenizer`, `pipeline`, `dataset`, `evaluation`, `fairness`, `bias`, `accuracy`, `loss`, `gradient`, `agent`, `llm`, `prompt`, `finetune` |
| 4 | Dependency files: `requirements.txt`, `requirements-ml.txt`, `pyproject.toml`, `setup.py`, `package.json` |
| 5 | AI-keyword YAML/JSON config files |

Skipped: `.git/`, `__pycache__/`, `.venv/`, `venv/`, `node_modules/`, `dist/`, `build/`.

---

## Supplementary documents

The three supplementary inputs are passed to Claude in both Stage 3 (analysis) and Stage 4 (test generation). The more specific and authoritative the input, the more precise the generated tests.

### File upload (PDF, DOCX, TXT, MD)

Best documents to upload:

| Document | What Claude learns from it |
|---|---|
| Data Processing Agreement (DPA) | Data retention periods → specific GDPR retention tests; data subject rights obligations → erasure process tests |
| Model Risk Policy | Risk appetite thresholds → specific pass/warn thresholds for technical tests |
| Product brief / PRD | User population and use case → which protected groups to target in fairness tests |
| Architecture doc | Data flows → which personal data the system actually touches |
| Compliance checklist | Which regulations apply → targeted regulatory tests |
| Previous audit report | Known gaps → tests that check if those gaps are still present |

**Example:** Attaching a DPA that specifies "training data must not include data older than 3 years" causes Claude to generate a test: "Check that training data pipeline enforces a 3-year retention cutoff."

### URL fetch

Paste any publicly accessible URL — Confluence page, internal wiki, GitHub model card, regulatory guidance page. HTML is stripped automatically; plain text is sent to Claude.

**Works well for:** hosted model cards, public compliance documentation, Confluence pages (if accessible), internal wikis.

**Does not work for:** pages behind SSO/login (the fetcher uses an unauthenticated request).

### Business context text area

Paste a plain-English description. Include:

- What the system does and what decisions it makes
- Who is affected (user population, demographic groups)
- Jurisdictions and applicable regulations
- Any known sensitive data types processed
- Specific vulnerable groups or high-risk use cases

**Example:**

> "This system predicts employee attrition risk for HR teams in the UK financial sector. It processes age, tenure, salary band, performance ratings, and absence history. Decisions inform redundancy planning and affect approximately 5,000 employees. We are subject to UK GDPR, the Equality Act 2010 (protected characteristics: age, gender, race, disability), and FCA requirements on operational resilience."

This causes Claude to generate tests for Equality Act protected characteristics, UK GDPR obligations, FCA resilience requirements, and HR-specific human oversight needs — not generic fairness checks.

---

## Scoring

The scanner uses the same Aegis Index formula as the persistent inventory mode:

```
pillar score = 100 × Σ(status_points × severity_weight) / Σ(severity_weight)
```

Scores are **ephemeral** — stored in Streamlit session state only, not in SQLite. They disappear on browser refresh. To persist results, export the page or take a screenshot.

---

## Limitations

- **AI-generated assessment, not compliance certification.** Claude evaluates evidence in the extracted files. It cannot access runtime systems, production databases, or internal APIs. A `pass` means the evidence was found in the repo — not that the system is compliant.
- **Quality depends on repo documentation.** A repo with no README, no model card and no comments will produce mostly `fail` or `warn` results, not because the system is ungoverned, but because there is no written evidence to find. Add documentation and re-scan.
- **Context window cap.** Only the first 80,000 characters of extracted content are sent to Claude. Very large repos may have relevant files beyond this cap. Add them as supplementary uploads if important.
- **12–15 generated tests.** The scanner generates a fixed range of tests per scan. It may not cover every applicable requirement for complex systems. Use the full YAML test library (41 tests) in inventory mode for complete coverage.
- **No historical comparison.** Each scan is independent. The scanner does not track changes over time.

---

## Tips for good results

1. **Upload a model card or README before scanning.** Even a brief one dramatically improves test precision.
2. **Name the regulation.** In the business context field, naming the specific regulation ("subject to EU AI Act high-risk classification") causes Claude to generate tests for that regulation's specific articles.
3. **Name the affected population.** "Used to screen job applicants in Germany" triggers age discrimination tests under AGG; "used for credit decisions in the US" triggers ECOA / FCRA tests.
4. **Upload your DPA.** It's the single document most likely to generate specific, actionable GDPR tests.
5. **For private repos.** Clone locally first with your credentials, then enter the local path in the scanner instead of the URL.
6. **Re-scan after adding docs.** If the first scan produces mostly `fail` results with "no evidence found", add a model card and re-scan. The score should improve significantly.
